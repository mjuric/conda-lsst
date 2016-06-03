import os
import os.path
import sys
import tempfile

import sqlalchemy
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import sessionmaker, make_transient

from requests.exceptions import HTTPError

# Have 'requests' actually be a session with the 'file://' adaptor mounted
# so we can read local files as well.
import requests
from requests_file import FileAdapter	# run 'pip install requests_file' if this fails
s = requests.Session()
s.mount('file://', FileAdapter())
requests = s

Base = declarative_base()
class Channel(Base):
	__tablename__  = 'channels'
	__table_args__ = {'sqlite_autoincrement': True}

	id       = Column(Integer, primary_key=True)
	urlbase  = Column(String)				# URL base

	# Relationship to Packages (in this Channel)
	packages = relationship('Package', backref='channel', lazy='dynamic', cascade='all, delete, delete-orphan')

class Package(Base):
	__tablename__ = 'packages'
	__table_args__ = (
		UniqueConstraint('name', 'version', 'build_number', 'channel_id'),
		{'sqlite_autoincrement': True}
	)

	id           = Column(Integer, primary_key=True)

	name         = Column(String)
	version      = Column(String)
	build_number = Column(Integer)

	recipe_hash  = Column(String)

	# Relationship to Channel
	channel_id   = Column(Integer, ForeignKey('channels.id'))
#	channel      = relationship("Channel", backref=backref("packages", order_by=id, lazy='dynamic'))
	

# From http://stackoverflow.com/a/6078058/897575
#   model: class to query or create
#   kwargs: {member=value} dict of class members
def get_or_create(session, model, **kwargs):
	instance = session.query(model).filter_by(**kwargs).first()
	if instance:
		return instance
	else:
		instance = model(**kwargs)
		session.add(instance)
		session.commit()
		return instance

class RecipeDB(object):
	server   = None
	channel  = None

	_db = None		# The loaded database (dict of dicts)

	def __init__(self, recipe_db_dir, platform):
		self._db = {}
		self.platform = platform

		# open the database, ensure the tables are defined
		dbfn = os.path.join(recipe_db_dir, platform, 'cache-db.sqlite')
		try:
			os.makedirs(os.path.dirname(dbfn))
		except OSError:
			pass				# dir already exists

		##engine = sqlalchemy.create_engine('sqlite:///:memory:', echo=True)
		engine = sqlalchemy.create_engine('sqlite:///%s' % dbfn, echo=False)
		Base.metadata.create_all(engine)

		# create a session
		self._session = sessionmaker(bind=engine)()

	def get_repodata(self, urlbase):
		# Fetch and parse repodate.json
		urlbase = '%s%s/' % (urlbase, self.platform)
		url = urlbase + 'repodata.json'
		r = requests.get(url)
		r.raise_for_status()
		return r.json()

	def files_to_upload(self):
		# FIXME: super-inefficient, loads the entire database to memory
		remote_channels = [ channel.id for channel in self._session.query(Channel).filter(~Channel.urlbase.like('file://%')).all() ]

		# Find packages that are present locally but not remotely
		packages = self._session.query(Package).all()
		all    = set([ (p.name, p.version, p.build_number) for p in packages ])
		remote = set([ (p.name, p.version, p.build_number) for p in packages if p.channel_id in remote_channels ])

		locals = [ p for p in packages if p.channel_id not in remote_channels ]
		to_upload = [ p for p in locals if (p.name, p.version, p.build_number) in (all - remote) ]

		# Find filenames
		pkg2fn = dict()
		for c in self._session.query(Channel).filter(Channel.urlbase.like('file://%')).all():
			pkg2fn[p.channel.urlbase] = pkgs = dict()
			base = os.path.join(p.channel.urlbase[len('file://'):], self.platform)
			repodata = self.get_repodata(c.urlbase)
			for fn, pkginfo in repodata[u'packages'].iteritems():
				name, version, build_number = pkginfo['name'], pkginfo['version'], pkginfo['build_number']
				assert (name, version, build_number) not in pkgs
				pkgs[(name, version, build_number)] = os.path.join(base, fn)

		filenames = [ pkg2fn[p.channel.urlbase][(p.name, p.version, p.build_number)] for p in to_upload ]
		return filenames
                                
	def hash_filelist(self, filelist, ignore_prefix='', open=open, verbose=False):
		import hashlib
		m = hashlib.sha1()

		if False:
			# Echo the output to the screen
			def update(m, s):
				sys.stdout.write("%s" % s)
				return m.update(s)
		else:
			def update(m, s): return m.update(s)

		for fn in sorted(filelist):
			# Ignore all files that *don't* end in the following suffixes
			suffixes = [ '.patch', '.yaml', '.patch', '.diff', '.sh' ]	# FIXME: make this configurable somehow
			for suffix in suffixes:
				if fn.endswith(suffix):
					break

				# Special handling for meta.yaml, to work around the change introduced in conda-build 1.20.3
				# https://github.com/conda/conda-build/commit/b4ec0e0659d8f376042d4fc391616bf235996cf5 where
				# meta.yaml is now stored in the recipe dir as meta.yaml.template
				if fn.endswith('/meta.yaml.template'):
					break
			else:
				continue

			mm = hashlib.sha1()
			with open(fn) as fp:
				rel_fn = fn[len(ignore_prefix):]

				# Special handling for meta.yaml, to work around the change introduced in conda-build 1.20.3
				# https://github.com/conda/conda-build/commit/b4ec0e0659d8f376042d4fc391616bf235996cf5 where
				# meta.yaml is now stored in the recipe dir as meta.yaml.template
				if rel_fn == 'meta.yaml.template':
					rel_fn = 'meta.yaml'

				# Special handling of some files:
				if rel_fn == 'meta.yaml':
					# remove build number and modify the build string from the meta.yaml file
					# build:
					#   number: 0
					#   string: "blah_0"
					state = 0	# 0: scan for build, 1: scan for number: 2: pass through the rest of the file
					buildnum = None
					for line in fp:
						if state == 0 and line == 'build:\n':
							state = 1
						elif state == 1 and line.strip().startswith('number:'):
							line = ''	# don't write out the build number
						elif state == 1 and line.strip().startswith('string:'):
							line = ''	# strip out the build string -- it encodes the buildnum as well
									# FIXME: not sure what happens if we decide to change the buildstr prefix?
						elif state == 1 and not line.strip():
							state = 2	# didn't have an explicit number:

						mm.update(line)
				else:
					# Just add the file contents
					mm.update(fp.read())

			# Update the list hash
			res = "%s  %s\n" % (mm.hexdigest(), rel_fn)
			update(m, res)
			if verbose:
				sys.stdout.write(res)

		return m.hexdigest()

	def reindex(self, channels):
		# Reindex the channels
		cids = []
		for urlbase in channels:
			channel = get_or_create(self._session, Channel, urlbase=urlbase)
			self.reindex_channel(channel)
			cids.append(channel.id)

		# Delete information for any channel that wasn't in the list above
		for channel in self._session.query(Channel).filter(~Channel.id.in_(cids)).all():
			print "purging cached data for [%s]... " % channel.urlbase,
			self._session.delete(channel)
			print "done."

		self._session.commit()

	def reindex_channel(self, channel):
		print "updating built package cache [from %s%s] " % (channel.urlbase, self.platform),

		urlbase = '%s%s/' % (channel.urlbase, self.platform)

		try:
			repodata_ = self.get_repodata(channel.urlbase)
		except HTTPError as e:
			# Local channels may not exist if nothing has been built with conda-build yet
			if channel.urlbase.startswith('file://'):
				print "  not found. skipping."
				return
			elif e.response.status_code == 404:
				# Assume this is a new, empty, channel
				print "  appears uninitialized. skipping."
				return
			else:
				raise

		# convert to something more useful...
		repodata = {}
		for package, pkginfo in repodata_[u'packages'].iteritems():
			name, version = [ pkginfo[s].encode('utf-8') for s in ['name', 'version'] ]
			build_number = pkginfo['build_number']
			repodata[(name, version, build_number)] = package

		# Delete all cache entries that don't have a counterpart in repodata
		# (e.g., files may have been deleted from the repository)
		for package in channel.packages:
			key = (package.name, package.version, package.build_number)
			if key not in repodata:
				#print "Would delete %s" % str(key)
				self._session.delete(package)
				sys.stdout.write("-")
				sys.stdout.flush()

		# Fetch each package, extract and hash its recipe
		import tarfile
		for (name, version, build_number), package in repodata.iteritems():
			# Skip if we already know about this package
			if channel.packages.filter(Package.name == name, Package.version == version, Package.build_number == build_number).count():
				# print "already know about %s, skipping." % package
				sys.stdout.write(".")
				sys.stdout.flush()
				continue

			# See if we know about this package in other channels; just copy the info if we do
			pkg = self._session.query(Package).filter_by(name=name, version=version, build_number=build_number).first()
			if pkg is not None:
				make_transient(pkg)
				pkg.id = None
				pkg.channel_id = channel.id
				self._session.add(pkg)

				sys.stdout.write("+")
				sys.stdout.flush()
				continue

			pkgurl = urlbase + package
			_, suffix = os.path.splitext(pkgurl)

			# Download the package
			with tempfile.NamedTemporaryFile(suffix=suffix) as fp:
				#print os.path.basename(pkgurl)
				download_url(pkgurl, fp)

				# Extract the recipe
				with tarfile.open(fp.name) as tf:
					prefix = 'info/recipe/'

					all = tf.getnames()
					info = [ fn for fn in all if fn.startswith(prefix) ]

					# hash all files in info/recipe/
					import contextlib
					hash = self.hash_filelist(info, prefix, open=lambda fn: contextlib.closing(tf.extractfile(fn)))

					# add to the database
					pkg = Package(name=name, version=version, build_number=build_number, recipe_hash=hash)
					channel.packages.append(pkg)

					try:
						ctr += 1
						if ctr == -1: break
					except:
						ctr = 0

				sys.stdout.write("+")
				sys.stdout.flush()

			# write out the new database
			self._session.commit()
		self._session.commit()
		print " done."

	def hash_recipe(self, recipe_dir, verbose=False):
		# Compute recipe hash for files in recipe_dir

		# Get all files (incl. those in directories) and sort them
		def listfiles(dir):
			for root, directories, filenames in os.walk(dir):
				for filename in filenames: 
					yield os.path.join(root, filename)

		filelist = list(listfiles(recipe_dir))
		prefix = recipe_dir if recipe_dir.endswith('/') else recipe_dir + '/'

		hash = self.hash_filelist(filelist, prefix, verbose=verbose)
		if verbose:
			print "result: ", hash
		return hash

	def get_next_buildnum(self, name, version):
		from sqlalchemy.sql import func
		max = self._session.query(func.max(Package.build_number)).filter(Package.name == name, Package.version == version).scalar()
		return max + 1 if max is not None else 0

	def __getitem__(self, key):
		# Return buildnum for (name, version, recipe_hash) if in the database
		name, version, recipe_hash = key
		package = self._session.query(Package).filter_by(name=name, version=version, recipe_hash=recipe_hash).first()
		if package is None:
			raise KeyError()
		else:
			return package.build_number

# Cribbed from http://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py
def download_url(url, fp):
	# Download the contents of url into a file-like object fp
	r = requests.get(url, stream=True)
	r.raise_for_status()

	for chunk in r.iter_content(chunk_size=10*1024*1024): 
		if chunk: # filter out keep-alive new chunks
			fp.write(chunk)
	fp.flush()

def test_release_db():
	db = RecipeDB()

	name, version = "eups", "1.5.9_1"
	dir = 'recipes/static/eups'
	#name, version = "lsst-palpy", "1.6.0002"
	#dir = 'recipes/generated/lsst-palpy'
	hash = db.hash_recipe(dir)
	print "hash for %s: %s" % (dir, hash)
#	exit()

	db.reindex(channels)

	print "next buildnum:", db.get_next_buildnum(name, version)
	print "hash lookup: ", db[name, version, hash]


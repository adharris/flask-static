import sys, re
import os
from os import path

from flask import current_app

from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.frozen import Freezer
from flask_static.models import create_model_base

from sqlalchemy.ext.declarative import has_inherited_table

import inflection
import yaml


class Static(object):

  def __init__(self, app=None, db=None, freezer=None):
    self.db = db or SQLAlchemy()
    self.freezer = freezer or Freezer(with_static_files=False)
    self.Model = create_model_base(self.db)
    self.app = app

    self._models = {}

    if app is not None:
      self.init_app(app)

  def init_app(self, app):

    app.config.setdefault("STATIC_MODELS_DIRECTORY", 'models')
    app.config.setdefault("STATIC_FILE_REGEXP",
      r'^((?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})-)?(?P<id>.*)\.(?P<format>.+)$')

    self.db.init_app(app)
    self.freezer.init_app(app)

    try:
      app.jinja_env.add_extension('jinja2_highlight.HighlightExtension')
    except:
      pass

    app.before_first_request(self.rebuild_database)

    with app.app_context():
      self.filenames = [str(f) for m, f in self.get_model_files()]


  def run(self, **options):
    options['extra_files'] =  options.get("extra_files", []) + self.filenames
    self.freezer.run(**options)


  def rebuild_database(self):
    print " * Rebuilding static database"
    self.db.drop_all()
    self.db.create_all()
    self.load_models()

  def load_models(self):
    for model, file_path in set(self.get_model_files()):
      f = open(file_path)
      fm, body = self.parse_frontmatter(f.read())
      f.close()
      self.db.session.add(model(file_path, fm, body))
    self.db.session.commit()

  def get_model_files(self):
    models_dir = path.join(current_app.root_path,
      current_app.config['STATIC_MODELS_DIRECTORY'])

    # Build a list of directories that have specific types of models
    search_paths = {models_dir: self.Model} 
    for model in self.Model.__subclasses__():
      for directory in model.model_directories():
        if not path.isabs(directory):
          directory = path.join(models_dir, directory)
        search_paths[directory] = model

    def model_dir_filter(dirpath):
      def f(dirname):
        full_path = path.join(dirpath, dirname)
        return full_path not in search_paths
      return f

    for directory, model in search_paths.items():
      for dirpath, dirnames, filenames in os.walk(str(directory)):
        dirnames[:] = filter(model_dir_filter(dirpath), dirnames)
        for filename in filenames:
          yield model, path.join(dirpath, filename)



  def parse_frontmatter(self, data):
    sep = re.compile(r'^---\s*$', re.M)
    separators = list(sep.finditer(data))

    if len(separators) == 0:
      front_matter = yaml.load(data)
      return front_matter, None

    if len(separators) >= 2:
      front_matter = data[separators[0].start(0):separators[1].start(0)]
      body = data[separators[1].end(0):]
      return yaml.load(front_matter), body

    return None, None


  def __getattr__(self, name):
    if name not in self._models:
      self._models[name] = self.Model.create_base(name)
    return self._models[name]


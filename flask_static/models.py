import re, datetime, os
from os import path

from flask import current_app, render_template_string, Markup

from sqlalchemy.ext.declarative import declared_attr, has_inherited_table

import inflection
import markdown

def create_model_base(db):
  class Model(db.Model):

    id   = db.Column(db.Integer(), primary_key=True)
    type = db.Column(db.String())

    model_id   = db.Column(db.String(), unique=True)
    published  = db.Column(db.Boolean())
    date       = db.Column(db.Date())
    filetype   = db.Column(db.String())

    title = db.Column(db.String())
    body  = db.Column(db.String())

    front_matter = db.Column(db.PickleType())

    @declared_attr
    def __mapper_args__(cls):
      if cls.__name__ == 'Model':
        return {'polymorphic_identity': 'model', 'polymorphic_on': 'type' } 
      else:
        return {'polymorphic_identity': cls.__tablename__, 'inherit_condition': Model.id == cls.id }

    @property
    def __directory__(self):
      return self.__name__.lower()

    def __init__(self, file_path, fm, body):
      filename = path.basename(file_path)
      match = re.search(current_app.config['STATIC_FILE_REGEXP'], filename)

      self.date = fm.pop('date', None) or \
                  match.group('date') or \
                  datetime.datetime.fromtimestamp(os.path.getctime(file_path))

      self.model_id = fm.pop('id',     "{0}.{1}".format(self.type, match.group('id')))
      self.format   = fm.pop('format', match.group('format'))

      self.published = fm.pop('published', True)

      self.title = fm.pop('title', inflection.titleize(match.group('id')))
      self.body = body

      for key in fm.keys():
        if hasattr(self, key):
          setattr(self, key, fm.pop(key))

      self.front_matter = fm

    @property
    def excerpt(self):
      content = self.body.split(current_app.config.get('EXCERPT_SEPARATOR', '\n\n'))[0]
      content = render_template_string(content, post=self)
      if self.filetype == '.md':
        content = markdown.markdown(content)
      return Markup(content)


    @classmethod
    def model_directories(cls):
      """
      Return the directories in which to look for models.

      Defaults to pluralized module name in the modules directory.
      """
      plural = inflection.pluralize(
        inflection.dasherize(inflection.underscore(cls.__name__))).lower()
      return [plural]

    @classmethod
    def create_base(cls, name):
      def mappers(cls):
        return {'polymorphic_identity': name}

      class NewModel(cls):
        @declared_attr
        def __mapper_args__(cls):
          return {'polymorphic_identity': name}
        __tablename__ = inflection.pluralize(inflection.underscore(name))
        id = db.Column(db.Integer, db.ForeignKey("model.id"), primary_key=True)
      NewModel.__name__ = name
      return NewModel

  return Model

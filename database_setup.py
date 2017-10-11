import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

'''Declare columns for the Users table'''
class Users(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	email = Column(String(250), nullable=False)
	picture = Column(String(250))

'''Declare columns for the Genres table'''
class Genres(Base):
	__tablename__ = 'genre'
	id = Column(Integer, primary_key = True)
	name = Column(String(80), nullable = False)
	user_id = Column(Integer, ForeignKey('users.id'))
	user = relationship(Users)

	'''To return the table data for JSON format'''
	@property
	def serialize(self):
	    return {
	    	'id': self.id,
	        'name': self.name,
	    }

'''Declare columns for tthe Games table'''
class Games(Base):
	__tablename__ = 'games'
	id = Column(Integer, primary_key = True)
	name = Column(String(80), nullable = False)
	description = Column(String(250))
	genre_id = Column(Integer, ForeignKey('genre.id'))
	genre = relationship(Genres)
	user_id = Column(Integer, ForeignKey('users.id'))
	user = relationship(Users)

	'''To return the table data for JSON Format'''
	@property
	def serialize(self):
	    return {
	        'genre': self.genre.name,
	        'description': self.description,
	        'name': self.name,
	    }

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.create_all(engine)


from collections import namedtuple, OrderedDict

import os
import sys

from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine, Column, ForeignKey, Unicode, UnicodeText, \
    Integer, String, Table, Unicode, Boolean, DateTime, Date, func
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///mydatabase.db')
Base = declarative_base()


ps_association_table = Table(
    'paper_search_association',
    Base.metadata,
    Column('paper_id', Integer, ForeignKey('papers.id')),
    Column('search_id', Integer, ForeignKey('searches.id'))
)

class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bibcode = Column(Unicode(20), nullable=False)
    title = Column(UnicodeText, default=None)
    abstract = Column(UnicodeText,default=None)
    pub_openaccess = Column(Boolean)
    refereed = Column(Boolean)
    doi = Column(Unicode(20), default=None)
    pubdate = Column(Date)
    first_added = Column(DateTime, default=func.now())
    updated = Column(DateTime, nullable=True,
                     onupdate=func.now())
    identifiers = relationship("Identifier")
    keywords = relationship("Keyword")
    properties = relationship("Property")
    authors = relationship("Author", order_by="Author.position_")
    searches = relationship("Search", secondary=ps_association_table)
    comments = relationship("Comment")

    def __repr__(self):
        return "<Paper(title={})>".format(self.title)


class Identifier(Base):
    __tablename__ = "identifiers"
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    paper_id = Column('paper_id', Integer,
           ForeignKey('papers.id', onupdate='RESTRICT', ondelete='RESTRICT'))
    identifier = Column('identifier', Unicode(20), nullable=False)
    paper = relationship("Paper")



class Author(Base):
    __tablename__ = 'authors'
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    paper_id = Column('paper_id', Integer,
           ForeignKey('papers.id', onupdate='RESTRICT', ondelete='RESTRICT'))
    author = Column('author', Unicode(20), nullable=False)
    position_ = Column('position_', Integer, nullable=False)
    affiliation = Column(UnicodeText)
    paper = relationship("Paper")
    def __repr__(self):
        return "<Author(author={})".format(self.author)


class Search(Base):
    __tablename__ = 'searches'
    id = Column(Integer, primary_key=True, autoincrement=True)
    named = Column(Unicode(50),nullable=False)
    ads_query = Column(UnicodeText)
    last_performed = Column(DateTime)
    startdate = Column(DateTime)
    timerange = Column(Integer)
    papertypes = relationship("PaperType", order_by="PaperType.position_")
    comments = relationship("Comment")
    infosections = relationship("InfoSection", order_by="InfoSection.position_")
    papers = relationship("Paper", secondary=ps_association_table)


class PaperType(Base):
    __tablename__ = 'paper_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(Integer, ForeignKey('searches.id',
                        onupdate='RESTRICT', ondelete='RESTRICT'),
                       nullable=False)
    position_ = Column(Integer)
    name_ = Column(UnicodeText)
    radio = Column(Boolean)
    search = relationship("Search")


class PaperTypeValue(Base):
    __tablename__ = 'papertype_value'
    id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(Integer, ForeignKey('comments.id',
                                onupdate='RESTRICT', ondelete='RESTRICT'),
                        nullable=False)
    papertype_id = Column(Integer, ForeignKey('paper_types.id',
                                              onupdate='RESTRICT', ondelete='RESTRICT'),
                          nullable=False)
    comment = relationship("Comment")
    papertype = relationship("PaperType")

class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(Integer, ForeignKey('searches.id',
                                onupdate='RESTRICT', ondelete='RESTRICT'),
                        nullable=False)
    paper_id = Column(Integer,
           ForeignKey('papers.id', onupdate='RESTRICT', ondelete='RESTRICT'))
    username = Column(Unicode(50), nullable=False)
    datetime = Column(DateTime, onupdate=func.now(), default=func.now())
    search = relationship("Search")
    paper = relationship("Paper")
    papertypevalues = relationship("PaperTypeValue")
    infosectionvalues = relationship("InfoSectionValue")



class InfoSection(Base):
    __tablename__ = 'info_sections'
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(Integer, ForeignKey('searches.id',
                        onupdate='RESTRICT', ondelete='RESTRICT'),
                       nullable=False)
    position_ = Column(Integer)
    name_ = Column(Unicode(50))
    type_ = Column(Integer)
#    /*0=radio, 1=check, 2=textarea, 3=textarea_newlines*/

    instructiontext =  Column(Unicode(50), default=None)
    search = relationship("Search")
    sublists = relationship("InfoSublist")



class InfoSectionValue(Base):
    __tablename__ = 'info_section_values'
    id = Column(Integer, primary_key=True, autoincrement=True)
    info_section_id=Column(Integer, ForeignKey('info_sections.id',
                                               onupdate='RESTRICT',
                                               ondelete='RESTRICT'),
                           nullable=False)
    comment_id = Column(Integer, ForeignKey('comments.id', onupdate='RESTRICT',
                                          ondelete='RESTRICT'),
                        nullable=False)
    info_sublist_id = Column(Integer, ForeignKey('info_sublists.id',
                                                 onupdate='RESTRICT',
                                                 ondelete='RESTRICT'),
                             nullable=True)
    entered_text = Column(UnicodeText)
    #entered_choice = Column(Integer)
    comment = relationship("Comment")
    infosection = relationship("InfoSection")
    infosublist = relationship("InfoSublist")


class InfoSublist(Base):
    __tablename__ = 'info_sublists'
    id = Column(Integer, primary_key=True, autoincrement=True)
    info_section_id = Column(Integer, ForeignKey('info_sections.id',
                                                 onupdate='RESTRICT',
                                                 ondelete='RESTRICT'),
                                                 nullable=False)
    named = Column(Unicode(50))
    position_ = Column(Integer)
    #entry_value = Column(Integer)
    section = relationship("InfoSection")

class Keyword(Base):
    __tablename__ = 'keywords'
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey('papers.id',
                                          onupdate='RESTRICT',
                                          ondelete='RESTRICT'))
    keyword = Column(Unicode(20), nullable=False)
    paper = relationship("Paper")

class Property(Base):
    __tablename__ = 'properties'
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey('papers.id',
                                          onupdate='RESTRICT',
                                          ondelete='RESTRICT'),
                                          nullable=False)
    property = Column(Unicode(30), nullable=False)
    paper = relationship("Paper")





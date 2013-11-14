# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": ["""
        CREATE TABLE "category" (
            id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""",
        'ALTER TABLE "thread" ADD COLUMN category_id INTEGER;',
        'CREATE UNIQUE INDEX "ix_category_name" ON "category" (name);',
        ],
    "postgres": ["""
        CREATE TABLE "category" (
            id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""", """
        CREATE SEQUENCE category_id_seq
            START WITH 1
            INCREMENT BY 1
            NO MAXVALUE
            NO MINVALUE
            CACHE 1
        ;""",
        "ALTER SEQUENCE category_id_seq OWNED BY category.id;",
        "ALTER TABLE ONLY category ALTER COLUMN id SET DEFAULT nextval('category_id_seq'::regclass);",
        'ALTER TABLE "thread" ADD COLUMN category_id INTEGER;',
        'ALTER TABLE "thread" ADD FOREIGN KEY (category_id) REFERENCES category(id);',
        'CREATE UNIQUE INDEX "ix_category_name" ON "category" (name);',
        ],
    "mysql": ["""
        CREATE TABLE `category` (
            id INTEGER NOT NULL AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""",
        'ALTER TABLE `thread` ADD COLUMN category_id INTEGER;',
        'ALTER TABLE `thread` ADD FOREIGN KEY (category_id) REFERENCES category(id);',
        'CREATE UNIQUE INDEX `ix_category_name` ON `category` (name);',
        ],
    }


def apply(store):
    """Add the category table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()

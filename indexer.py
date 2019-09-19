#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys
import argparse
import unicodedata
import string
import configparser
import subprocess
from shutil import rmtree
import io

BASE = "base"
TITLE_LEVEL = 2

#folders
LINKS = None
BOARD = None
THUMB = None

INDEX = None
SUMMARY = None

VIEW = None
PPR = None
EMPTY_IMG = None

TAG_SYM = "#"
CAT_SYM = "$"
DATE_SYM = "¢"
AUTHOR_SYM = "£"
SUBTITLE_SYM = "&"

class ItemGenerator:
    
    @staticmethod
    def make_from_hook(hook):
        readme_path = Item.getReadme(hook)
        Item.verify(hook)
        with open(readme_path, "r") as readme:
            return Item(hook, readme.readlines()[0][:-1])

    # load item description from a single line in BOARD
    @staticmethod
    def make_from_line(line):
        if(line[-1] == "\n"): #removing \n
            line = line[:-1]
        parts = line.split(":")
        return Item(parts[1].strip(), parts[2].strip())

def onlyHashtags(word):
    for c in word:
        if c != '#':
            return False
    return True

def splitList(list, prefix):
    first = [x[1:] for x in list if x.startswith(prefix)]
    second = [x for x in list if not x.startswith(prefix)]
    return first, second

def getFirst(lista):
    if len(lista) > 0:
        return lista[0]
    return None

class Item:
    # get first line from file to mount Item
    def __init__(self, hook, line):
        if line[-1] == '\n':
            line = line[:-1]
        words = line.split(" ")
        if onlyHashtags(words[0]):
            del words[0] ##removing ##
        self.__fulltitle = " ".join(words) #removing the ##
        self.hook = hook # directory
        words     = [x     for x in words if not onlyHashtags(x)]
        self.tags , words = splitList(words, TAG_SYM)
        self.cat  , words = splitList(words, CAT_SYM)
        self.date , words = splitList(words, DATE_SYM)
        self.author,words = splitList(words, AUTHOR_SYM)
        parts = " ".join(words).split(SUBTITLE_SYM)
        self.title = parts[0].strip() if len(parts) > 0 else ''
        self.subtitle = parts[1].strip() if len(parts) > 1 else None
        self.cat = getFirst(self.cat)
        self.date = getFirst(self.date)
        self.author = getFirst(self.author)

    def getFulltitle(self):
        out = ''
        if self.date != None:
            out += DATE_SYM + self.date + ' '
        if self.cat != None:
            out += CAT_SYM + self.cat + ' '
        out += self.title
        if self.subtitle != None:
            out += ' ' + SUBTITLE_SYM + ' ' + self.subtitle
        for tag in self.tags:
            out += ' ' + TAG_SYM + tag
        if self.author != None:
            out += ' ' + AUTHOR_SYM + self.author

        return out

    @staticmethod
    def getReadme(hook):
        return BASE + os.sep + hook + os.sep + "Readme.md"

    @staticmethod
    def verify(hook):
        readme_path = Item.getReadme(hook)
        data = []
        fulltext = ""
        with open(readme_path, "r") as f:
            data = f.readlines()
            fulltext = "".join(data)

        if len(data) == 0:
            print("file empty ", hook)
            data.append('#' * TITLE_LEVEL + " Empty #empty\n")

        words = data[0].split(' ')
        if words[0] != "#" * TITLE_LEVEL:
            print("adicionando", '#' * TITLE_LEVEL, "em", hook)
            if onlyHashtags(words[0]):
                words[0] = "#" * TITLE_LEVEL
            else:
                data[0] = '#' * TITLE_LEVEL + " " + data[0]

        if len(data) == 2:
            words = data[0].split(" ")
            if not "#empty" in words and not "#empty\n" in words:
                print("adicionado marcador #empty em", hook)
                data[0] = data[0][:-1] + " #empty\n"
        
        if fulltext != "".join(data):
            with open(readme_path, "w") as f:
                f.write("".join(data))

    def getBoardEntry(self):
        levels = BOARD.split(os.sep)
        prefix = "../" * (len(levels) - 1)
        return "[](" + prefix + Item.getReadme(self.hook) + ') : ' + self.hook + " : " + self.getFulltitle()
        #return self.getCsv()

    def getMdLink(self):
        title = self.getFulltitle()
        title = title.lower()
        out = ''
        for c in title:
            if c == ' ' or c == '-':
                out += '-'
            elif c.isalnum():
                out += c
        return out
    
    def __str__(self):
        out = "@" + str(self.hook) + " "
        out += "[title: " + str(self.title) + "]"
        if self.cat:
            out += "[cat: " + self.cat + "]"
        if self.date:
            out += "[date: " + self.date + "]"
        if len(self.tags) > 0:
            out += "[tags: " + ", ".join(self.tags) + "]"
        if self.author:
            out += "[author: " + self.author + "]"
        return out
        

class Itens:
    def __init__(self):
        self.itens = []

    def parseFromFolders(self):
        hooks = os.listdir(BASE)
        hooks = [x for x in hooks if os.path.isdir(BASE + os.sep + x)]
        for hook in hooks: 
            try:
                self.itens.append(ItemGenerator.make_from_hook(hook))
            except FileNotFoundError as e:
                print(e)

    def parseFromBoard(self):
        with open(BOARD, "r") as f:
            names_list = [x for x in f.readlines() if x != "\n"]
            for line in names_list:
                self.itens.append(ItemGenerator.make_from_line(line))
        
    def __str__(self):
        return "\n".join(str(v) for v in self.itens)

    def generateBoard(self):
        self.itens.sort(key=lambda x: x.getFulltitle())
        with open(BOARD, "w") as names:
            names.write("\n".join([x.getBoardEntry() for x in self.itens]) + "\n")

    def updateTitles(self):
        for item in self.itens:
            data = []
            readme_path = BASE + os.sep + item.hook + os.sep + "Readme.md"
            if not os.path.exists(BASE + os.sep + item.hook): # folder not found
                print("folder", item.hook, "not found, creating")
                os.mkdir(BASE + os.sep + item.hook)
                with open(readme_path, "w") as f:
                    f.write('#' * TITLE_LEVEL + " " + item.getFulltitle() + " #empty\n")
            else:                
                with open(readme_path, "r") as f: #updating first line content
                    data = f.readlines()
                old_first_line = data[0]
                new_first_line = '#' * TITLE_LEVEL + " " +  item.getFulltitle() + "\n"
                if(old_first_line != new_first_line):
                    with open(readme_path, "w") as f: #reescreve linha 0
                        data[0] = new_first_line
                        f.write("".join(data))

    def generateLinks(self):
        rmtree(LINKS, ignore_errors=True)
        os.mkdir(LINKS)
        levels = LINKS.split(os.sep)
        prefix = "../" * len(levels)
        for item in self.itens:
            with open(LINKS + os.sep + item.title.strip() + ".md", "w") as f:
                f.write("[LINK](" + prefix + BASE + os.sep + item.hook + os.sep + "Readme.md)\n")

    @staticmethod
    def tree_generate(itens):
        tree = {}
        for item in itens:
            if item.cat == None:
                if not '_' in tree:
                    tree['_'] = []
                tree['_'].append(item)
            else:
                if not item.cat in tree:
                    tree[item.cat] = []
                tree[item.cat].append(item)
        return tree

    @staticmethod
    def makeRow(data):
        a = ""
        b = ""
        c = ""
        a += data[0][0]
        b += "-"
        c += data[0][1]
        for elem in data[1:]:
            a += "|" + elem[0]
            b += "|-"
            c += "|" + elem[1]
        a += "\n"
        b += "\n"
        c += "\n\n\n"
        return a, b, c

    @staticmethod
    def makeTableEntry(lista, prefix):
        data = []
        for item in lista:
            title = item.title
            if item.date:
                title = item.date + "<br>" + title
            sourceReadme = prefix + BASE + os.sep + item.hook + os.sep + "Readme.md"
            sourceThumb  = prefix + THUMB + os.sep + item.hook + ".jpg"

            entry = "[![](" + sourceThumb + ")](" + sourceReadme + ")"
            data.append([entry, title])
        
        while len(data) % PPR != 0:
            data.append(["![](" + EMPTY_IMG + ")", "-"])
        
        lines = []
        for i in range(0, len(data), PPR):
            a, b, c = Itens.makeRow(data[i: i + PPR])
            lines += [a, b, c]
        return "".join(lines)

    @staticmethod
    def makeThumb(hook):
        source = BASE  + os.sep + hook + os.sep + "__capa.jpg"
        destin = THUMB + os.sep + hook + ".jpg"
        if not os.path.isdir(THUMB):
            print("folder missing ", THUMB)
            exit(1)
        if not os.path.isfile(destin) or os.path.getmtime(source) > os.path.getmtime(destin):
            print("gerando thumb for", hook)
            cmd = ['convert', source, '-resize', '380x200>', destin]
            subprocess.run(cmd)

    def generateView(self):
        for item in self.itens:
            Itens.makeThumb(item.hook)
        tree = Itens.tree_generate(self.itens)
        view_text = io.StringIO()
        view_text.write("## @qxcode\n\n")
        levels = VIEW.split(os.sep)
        prefix = "../" * (len(levels) - 1)

        for cat, lista in tree.items():
            view_text.write("\n### " + cat + "\n\n")
            lista.sort(key=lambda x: x.getFulltitle(), reverse = True) 
            text = Itens.makeTableEntry(lista, prefix)
            view_text.write(text)
        
        with open(VIEW, "w") as f:
            f.write(view_text.getvalue())

    # update Readme.md
    def generateIndex(self):
        self.itens.sort(key=lambda x: x.getFulltitle())
        tree = Itens.tree_generate(self.itens)
        summary = io.StringIO()
        readme_text = io.StringIO()
        readme_text.write("## @qxcode\n\n")
        readme_text.write("## " + "Categorias" + "\n\n")

        levels = INDEX.split(os.sep)
        prefix = "../" * (len(levels) - 1)

        for cat, lista in tree.items():
            readme_text.write("\n### " + cat + "\n\n")
            summary.write("#" + cat + "\n")
            lista.sort(key=lambda x: x.title) #todo incluir data aqui para ordenar por data se houver?
            for item in lista:
                summary.write(item.hook + " ")
                readme_path = BASE + os.sep + item.hook + os.sep + "Readme.md"
                entry = "- [" + item.title.strip() + "](" + prefix + readme_path + "#" + item.getMdLink() + ")\n"
                readme_text.write(entry)
            summary.write("\n\n")
        
        if INDEX != None:
            with open(INDEX, "w") as f:
                f.write(readme_text.getvalue())

        if SUMMARY != None:
            with open(SUMMARY, "w") as f:
                f.write(summary.getvalue())
            readme_text.close()
            summary.close()

def getConfig(config, entryName, predicate, defaultValue):
    if entryName in config and predicate(config[entryName]):
        return config[entryName]
    else:
        return defaultValue

def loadGlobals():
    config = configparser.ConfigParser()
    file = ".config.ini"
    if not os.path.isfile(file):
        print("create a config.ini like in https://github.com/senapk/indexer")
        exit(1)
    try:
        print("loading", file)
        config.read(file)
        global BASE, LINKS, SUMMARY, BOARD, INDEX, TITLE_LEVEL, VIEW, PPR, EMPTY_IMG, THUMB
        BASE    = getConfig(config['DEFAULT'], "base"   , lambda x : x != '', 'base')
        indexer = config["indexer"]
        INDEX   = getConfig(indexer, "index"  , lambda x : x != '', None)
        BOARD   = getConfig(indexer, "board"  , lambda x : x != '', None)
        SUMMARY = getConfig(indexer, "summary", lambda x : x != '', None)
        LINKS   = getConfig(indexer, "links"  , lambda x : x != '', None)
        VIEW    = getConfig(indexer, "view"  , lambda x : x != '', None)
        THUMB   = getConfig(indexer, "thumb"  , lambda x : x != '', None)
        PPR     = int(getConfig(indexer, "posts_per_row"  , lambda x : x != '', 4))
        EMPTY_IMG = getConfig(indexer, "empty"  , lambda x : x != '', "-")
        TITLE_LEVEL = int(getConfig(indexer, "title_level", lambda x : x.isdigit(), 2))

    except configparser.NoSectionError as e:
        print("Entry section found:", e)
        exit(1)

def main():
    parser = argparse.ArgumentParser(prog='indexer.py')
    parser.add_argument('-s', action='store_true', help='set titles using names.txt')
    args = parser.parse_args()
    
    loadGlobals()

    itens = Itens()
    if args.s:
        print("obtendo nomes do arquivo names.txt")
        itens.parseFromBoard()
        itens.updateTitles()
        itens = Itens()
        itens.parseFromFolders()
    else:
        print("obtendo nomes dos títulos dos arquivos")
        itens.parseFromFolders()

    if BOARD != None:
        itens.generateBoard()
    if SUMMARY != None or INDEX != None:
        itens.generateIndex()
    if LINKS != None:
        itens.generateLinks()
    if VIEW != None:
        itens.generateView()
    print("all done")


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os, sys
import argparse
import unicodedata
import string
import configparser
import subprocess
from shutil import rmtree
from collections import namedtuple

import io

CFG = {}

class Hook:
    @staticmethod
    def getReadmePath(hook):
        return CFG.base_dir + os.sep + hook + os.sep + "Readme.md"

    @staticmethod
    def verify(hook):
        readme_path = Hook.getReadmePath(hook)
        data = []
        fulltext = ""
        with open(readme_path, "r") as f:
            data = f.readlines()
            fulltext = "".join(data)

        if len(data) == 0:
            print("file empty ", hook)
            data.append('#' * CFG.title_level + " Empty #empty\n")

        words = data[0].split(' ')

        def onlyHashtags(x): return len(x) == x.count("#")

        if words[0] != "#" * CFG.title_level:
            print("adicionando", '#' * CFG.title_level, "em", hook)
            if onlyHashtags(words[0]):
                words[0] = "#" * CFG.title_level
            else:
                data[0] = '#' * CFG.title_level + " " + data[0]

        if len(data) == 2:
            words = data[0].split(" ")
            if not "#empty" in words and not "#empty\n" in words:
                print("adicionado marcador #empty em", hook)
                data[0] = data[0][:-1] + " #empty\n"
        
        if fulltext != "".join(data):
            with open(readme_path, "w") as f:
                f.write("".join(data))

    @staticmethod
    def makeThumb(hook):
        source = CFG.base_dir  + os.sep + hook + os.sep + "__capa.jpg"
        destin = CFG.thumb_dir + os.sep + hook + ".jpg"
        if not os.path.isdir(CFG.thumb_dir):
            print("folder missing ", CFG.thumb_dir)
            exit(1)
        if not os.path.isfile(destin) or os.path.getmtime(source) > os.path.getmtime(destin):
            print("gerando thumb for", hook)
            cmd = ['convert', source, '-resize', '380x200>', destin]
            subprocess.run(cmd)

    @staticmethod
    def makeItem(hook):
        readme_path = Hook.getReadmePath(hook)
        Hook.verify(hook)
        with open(readme_path, "r") as readme:
            return Item(hook, readme.readlines()[0][:-1])

class Item:
    def __init__(self, hook, line):
        if line[-1] == '\n':
            line = line[:-1]
        words = line.split(" ")

        def onlyHashtags(x): return len(x) == x.count("#")
        if onlyHashtags(words[0]):
            del words[0] # removing ##
        self.hook = hook
        words = [x     for x in words if not onlyHashtags(x)]

        #list, prefix
        def splitList(l, p): return [x[1:] for x in l if x.startswith(p)], [x for x in l if not x.startswith(p)]

        self.tags , words = splitList(words, CFG.symbols.tag)
        self.cat  , words = splitList(words, CFG.symbols.category)
        self.date , words = splitList(words, CFG.symbols.date)
        self.author,words = splitList(words, CFG.symbols.author)
        parts = " ".join(words).split(CFG.symbols.subtitle)
        self.title = parts[0].strip() if len(parts) > 0 else ''
        self.subtitle = parts[1].strip() if len(parts) > 1 else None
        
        def getFirst(lista): return lista[0] if len(lista) > 0 else None

        self.cat = getFirst(self.cat)
        self.date = getFirst(self.date)
        self.author = getFirst(self.author)

    def getReadmePath(self):
        return CFG.base_dir + os.sep + self.hook + os.sep + "Readme.md"
    
    def getCover(self):
        return CFG.base_dir + os.sep + self.hook + os.sep + "__capa.jpg"

    def getFulltitle(self):
        out = ''
        if self.date != None:
            out += CFG.symbols.date + self.date + ' '
        if self.cat != None:
            out += CFG.symbols.category + self.cat + ' '
        out += self.title
        if self.subtitle != None:
            out += ' ' + CFG.symbols.subtitle + ' ' + self.subtitle
        for tag in self.tags:
            out += ' ' + CFG.symbols.tag + tag
        if self.author != None:
            out += ' ' + CFG.symbols.author + self.author

        return out

    def getBoardEntry(self):
        levels = CFG.board.split(os.sep)
        prefix = "../" * (len(levels) - 1)
        return "[](" + prefix + self.getReadmePath() + ') : ' + self.hook + " : " + self.getFulltitle()

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
        hooks = os.listdir(CFG.base_dir)
        hooks = [x for x in hooks if os.path.isdir(CFG.base_dir + os.sep + x)]
        for hook in hooks: 
            try:
                self.itens.append(Hook.makeItem(hook))
            except FileNotFoundError as e:
                print(e)

    def parseFromBoard(self):
        with open(CFG.board, "r") as f:
            names_list = [x for x in f.readlines() if x != "\n"]
            for line in names_list:
                parts = line.split(":")
                self.itens.appen(Item(parts[1].strip(), parts[2].strip()))
        

    def generateBoard(self):
        self.itens.sort(key=lambda x: x.getFulltitle())
        with open(CFG.board, "w") as names:
            names.write("\n".join([x.getBoardEntry() for x in self.itens]) + "\n")

    def updateTitles(self):
        for item in self.itens:
            data = []
            if not os.path.exists(CFG.base_dir + os.sep + item.hook): # folder not found
                print("folder", item.hook, "not found, creating")
                os.mkdir(CFG.base_dir + os.sep + item.hook)
                with open(item.getReadmePath(), "w") as f:
                    f.write('#' * CFG.title_level + " " + item.getFulltitle() + " #empty\n")
            else:                
                with open(item.getReadmePath(), "r") as f: #updating first line content
                    data = f.readlines()
                old_first_line = data[0]
                new_first_line = '#' * CFG.title_level + " " +  item.getFulltitle() + "\n"
                if(old_first_line != new_first_line):
                    with open(item.getReadmePath(), "w") as f: #reescreve linha 0
                        data[0] = new_first_line
                        f.write("".join(data))

    def generateLinks(self):
        rmtree(CFG.links_dir, ignore_errors=True)
        os.mkdir(CFG.links_dir)
        levels = CFG.links_dir.split(os.sep)
        prefix = "../" * len(levels)
        for item in self.itens:
            with open(CFG.links_dir + os.sep + item.title.strip() + ".md", "w") as f:
                f.write("[LINK](" + prefix + item.getReadmePath() + ")\n")

    @staticmethod
    def __tree_generate(itens):
        tree = {}
        for item in itens:
            if item.cat == None:
                if not CFG.orphan_cat in tree:
                    tree[CFG.orphan_cat] = []
                tree[CFG.orphan_cat].append(item)
            else:
                if not item.cat in tree:
                    tree[item.cat] = []
                tree[item.cat].append(item)
        return tree

    @staticmethod
    def __makeRow(data):
        a = "|".join([x[0] for x in data]) + "\n"
        b = "|".join(["-"] * len(data)) + "\n"
        c = "|".join([x[1] for x in data]) + "\n\n\n"
        return a, b, c

    @staticmethod
    def __makeTableEntry(lista, prefix):
        data = []
        for item in lista:
            sourceThumb  = prefix + CFG.thumb_dir + os.sep + item.hook + ".jpg"
            entry = "[![](" + sourceThumb + ")](" + item.getReadmePath() + ")"
            if item.date:
                data.append([entry, "@" + item.date + "<br>" + item.title])
            else:
                data.append([entry, "@" + item.hook + "<br>" + item.title])
        
        while len(data) % CFG.posts_per_row != 0:
            if CFG.empty_fig != None:
                data.append(["![](" + CFG.empty_fig + ")", "-"])
            else:
                data.append(["-", "-"])
        
        lines = []
        for i in range(0, len(data), CFG.posts_per_row):
            a, b, c = Itens.__makeRow(data[i: i + CFG.posts_per_row])
            lines += [a, b, c]
        return "".join(lines)

    def generateView(self):
        for item in self.itens:
            Hook.makeThumb(item.hook)

        self.itens.sort(key=lambda x: x.getFulltitle())
        tree = Itens.__tree_generate(self.itens)
        view_text = io.StringIO()
        view_text.write("## @qxcode\n\n")
        levels = CFG.view.split(os.sep)
        prefix = "../" * (len(levels) - 1)

        for cat, lista in tree.items():
            view_text.write("\n### " + cat + "\n\n")
            lista.sort(key=lambda x: x.getFulltitle(), reverse = CFG.reverse_sort)
            text = Itens.__makeTableEntry(lista, prefix)
            view_text.write(text)
        
        with open(CFG.view, "w") as f:
            f.write(view_text.getvalue())

    # update Readme.md
    def generateIndex(self):
        tree = Itens.__tree_generate(self.itens)
        summary = io.StringIO()
        readme_text = io.StringIO()
        readme_text.write("## @qxcode\n\n")
        readme_text.write("## " + "Categorias" + "\n\n")

        levels = CFG.index.split(os.sep)
        prefix = "../" * (len(levels) - 1)

        for cat, lista in tree.items():
            readme_text.write("\n### " + cat + "\n\n")
            lista.sort(key=lambda x: x.getFulltitle())
            for item in lista:
                entry = "- [" + item.title.strip() + "](" + prefix + item.getReadmePath() + "#" + item.getMdLink() + ")\n"
                readme_text.write(entry)
        
        if CFG.index != None:
            with open(CFG.index, "w") as f:
                f.write(readme_text.getvalue())

    def generateSummary(self):
        tree = Itens.__tree_generate(self.itens)
        summary = io.StringIO()
        for cat, lista in tree.items():
            summary.write("#" + cat + "\n")
            for item in lista:
                summary.write(item.hook + " ")
            summary.write("\n\n")
        with open(CFG.summary, "w") as f:
            f.write(summary.getvalue())
        summary.close()

    def __str__(self):
        return "\n".join(str(v) for v in self.itens)

def loadGlobals():
    if not os.path.isfile(".config.json"):
        print("create a .config.json like in https://github.com/senapk/indexer")
        exit(1)
    with open(".config.json", "r") as f:
        def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
        global CFG
        CFG = json.load(f, object_hook=_json_object_hook)

def main():
    parser = argparse.ArgumentParser(prog='indexer.py')
    parser.add_argument('-s', action='store_true', help='set titles using names.txt')
    args = parser.parse_args()
    
    loadGlobals()

    itens = Itens()
    if args.s:
        print("obtendo nomes do board")
        itens.parseFromBoard()
        itens.updateTitles()
        #reload and sort
        itens = Itens()
        itens.parseFromFolders()
    else:
        print("obtendo nomes das pastas")
        itens.parseFromFolders()

    if CFG.board != None:
        itens.generateBoard()
    if CFG.index != None:
        itens.generateIndex()
    if CFG.summary != None:
        itens.generateSummary()
    if CFG.links_dir != None:
        itens.generateLinks()
    if CFG.view != None:
        itens.generateView()
    print("all done")


if __name__ == '__main__':
    main()
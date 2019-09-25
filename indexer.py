#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os, sys
import argparse
import unicodedata
import string
import configparser
import subprocess
import re
from shutil import rmtree
from collections import namedtuple

import io

def loadConfig():
    if not os.path.isfile(".indexer.json"):
        print("fail: create a .indexer.json like in https://github.com/senapk/indexer")
        exit(1)
    with open(".indexer.json", "r") as f:
        cfg = json.load(f)
        cfg["board"] = os.path.join(cfg["config"],"board.md")
        cfg["links"] = os.path.join(cfg["config"], "links")
        cfg["thumbs"] = os.path.join(cfg["config"], "thumbs")
        return cfg

def splitPath(path):
    vet = os.path.normpath(path).split(os.path.sep)
    return os.sep.join(vet[0:-1]), vet[-1]

def verifyFile(path):
    readme_path = path
    lines = []
    fulltext = ""
    with open(readme_path, "r") as f:
        lines = f.readlines()
        fulltext = "".join(lines)

    if len(lines) == 0:
        print("file empty ", readme_path)
        lines.append("# Empty #empty\n")

    if len(lines) == 1:
        lines[0] += '\n\n'
    words = lines[0].split(' ')

    def onlyHashtags(x): return len(x) == x.count("#")
    
    if fulltext != "".join(lines):
        with open(readme_path, "w") as f:
            f.write("".join(lines))

def getMdLink(title):
    title = title.lower()
    out = ''
    for c in title:
        if c == ' ' or c == '-':
            out += '-'
        elif c == '_':
            out += '_'
        elif c.isalnum():
            out += c
    return out


class Item:
    cfg = {}

    def __init__(self, path, line):
        symbols = Itens.cfg["symbols"]
        if line[-1] == '\n':
            line = line[:-1]
        words = line.split(" ")
        def onlyHashtags(x): return len(x) == x.count("#")
        
        self.nivel = ""
        if onlyHashtags(words[0]):
            self.nivel = words[0]
            del words[0] # removing ##

        self.crude_title = " ".join(words)
        self.path = path
        self.hook = path.split(os.sep)[-2]
        words = [x     for x in words if not onlyHashtags(x)]

        #list, prefix
        def splitList(l, p): return [x[1:] for x in l if x.startswith(p)], [x for x in l if not x.startswith(p)]

        self.tags , words = splitList(words, symbols["tag"])
        self.cat  , words = splitList(words, symbols["category"])
        self.date , words = splitList(words, symbols["date"])
        self.author,words = splitList(words, symbols["author"])
        parts = " ".join(words).split(symbols["subtitle"])
        self.title = parts[0].strip() if len(parts) > 0 else ''
        self.subtitle = parts[1].strip() if len(parts) > 1 else None
        
        def getFirst(lista): return lista[0] if len(lista) > 0 else None

        self.cat = getFirst(self.cat)
        self.date = getFirst(self.date)
        self.author = getFirst(self.author)

    def getCover(self):
        root, file = splitPath(self.path)
        with open(self.path, "r") as f:
            text = f.read()
            regex = r"!\[(.*?)\]\(([^:]*?)\)"
            match = re.search(regex, text)
            if match:
                return os.path.join(root, match.group(2))
        return None

    def getThumb(self):
        cover = self.getCover()
        if cover:
            cover = os.sep.join(os.path.normpath(cover).split(os.path.sep)[1:]) #remove base
            return os.path.join(Item.cfg["thumbs"], cover)
        return None

    def makeThumb(self):
        cover = self.getCover()
        thumb = self.getThumb()
        thumbs_dir = Item.cfg["thumbs"]
        if cover == None or not os.path.isfile(cover):
            print("warning: missing cover on", self.path)
            return

        if not os.path.isdir(thumbs_dir):
            print("fail: thumb folder missing ", thumbs_dir)
            exit(1)

        if not os.path.isfile(thumb) or os.path.getmtime(cover) > os.path.getmtime(thumb):
            root, file = splitPath(thumb)
            if not os.path.isdir(root):
                os.makedirs(root)
            print("- making thumb for", self.path)
            cmd = ['convert', cover, '-resize', '320x180>', thumb]
            subprocess.run(cmd)

    def getFulltitle(self):
        symbols = Itens.cfg["symbols"]
        out = ''
        if self.date != None:
            out += symbols["date"] + self.date + ' '
        if self.cat != None:
            out += symbols["category"] + self.cat + ' '
        out += self.title
        if self.subtitle != None:
            out += ' ' + symbols["subtitle"] + ' ' + self.subtitle
        for tag in self.tags:
            out += ' ' + symbols["tag"] + tag
        if self.author != None:
            out += ' ' + symbols["author"] + self.author

        return out

    def getBoardEntry(self):
        levels = Itens.cfg["board"].split(os.sep)
        prefix = "../" * (len(levels) - 1)
        path = (prefix + self.path).replace("/./", "/")
        return "[](" + path + ')', self.nivel + " " + self.getFulltitle()

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
    cfg = {}
    def __init__(self):
        self.itens = []

    def parseFromFolders(self):
        base = Itens.cfg["base"]
        for (root, dirs, files) in os.walk(base, topdown=True):
            folder = root.split(os.sep)[-1]
            if folder.startswith("__") or folder.startswith("."):
                continue
            if(root.count(os.sep) - base.count(os.sep) != 1): #one level only
                continue
            files = [x for x in files if x.endswith(".md")]
            for file in files:
                path = os.path.join(root, file)
                verifyFile(path)
                with open(path, "r") as readme:
                    self.itens.append(Item(path, readme.readlines()[0][:-1]))

    def parseFromBoard(self):
        with open(Item.cfg["board"], "r") as f:
            names_list = [x for x in f.readlines() if x != "\n"]
            for line in names_list:
                parts = line.split(":")
                path = parts[0].strip()[6:-1]
                self.itens.append(Item(path, parts[1].strip()))

    def generateBoard(self):
        self.itens.sort(key=lambda x: x.getFulltitle())
        paths = []
        descriptions = []
        maxLen = 0
        for x in self.itens:
            path, description = x.getBoardEntry()
            if len(path) > maxLen:
                maxLen = len(path)
            paths.append(path)
            descriptions.append(description)
        paths = [x.ljust(maxLen) for x in paths]
        with open(Itens.cfg["board"], "w") as names:
            for i in range(len(paths)):
                names.write(paths[i] + " : " + descriptions[i] + "\n")

    def updateTitles(self):
        for item in self.itens:
            data = []
            if not os.path.isfile(item.path):
                root, file = splitPath(item.path)
                if not os.path.isdir(root):
                    os.makedirs(root)
                print("warning: file", item.path, "not found, creating!")
                with open(item.path, "w") as f:
                    f.write('##' + " " + item.getFulltitle() + " #empty\n")
            else:
                with open(item.path, "r") as f: #updating first line content
                    data = f.readlines()
                old_first_line = data[0]
                new_first_line = item.nivel + " " +  item.getFulltitle() + "\n"
                if(old_first_line != new_first_line):
                    with open(item.path, "w") as f: #reescreve linha 0
                        data[0] = new_first_line
                        f.write("".join(data))

    def generateLinks(self):
        links = Itens.cfg["links"]
        rmtree(links, ignore_errors=True)
        os.mkdir(links)
        levels = links.split(os.sep)
        prefix = "../" * len(levels)
        for item in self.itens:
            path = os.path.join(links, item.title.strip() + ".md")
            with open(path, "w") as f:
                path = (prefix + item.path).replace("/./", "/")
                f.write("[LINK](" + path + ")\n")

    def tree_generate_cat(self):
        tree = {}
        orphan_label = Itens.cfg["extra"]["orphan"]
        for item in self.itens:
            if item.cat == None:
                if not orphan_label in tree:
                    tree[orphan_label] = []
                tree[orphan_label].append(item)
            else:
                if not item.cat in tree:
                    tree[item.cat] = []
                tree[item.cat].append(item)
        return tree

    def tree_generate_tag(self):
        tree = {}
        orphan_label = Itens.cfg["extra"]["orphan"]
        for item in self.itens:
            if len(item.tags) == 0:
                if not orphan_label in tree:
                    tree[orphan_label] = []
                tree[orphan_label].append(item)
            else:
                for tag in item.tags:
                    if not tag in tree:
                        tree[tag] = []
                    tree[tag].append(item)
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
        empty_fig = Item.cfg["extra"]["empty_fig"]
        posts_per_row = Item.cfg["extra"]["posts_per_row"]
        for item in lista:
            thumb = item.getThumb()
            if thumb != None:
                thumb = prefix + thumb
            else:
                if empty_fig:
                    thumb = prefix + empty_fig
                else:
                    thumb = "https://placekitten.com/320/181"
            entry = "[![](" + thumb + ")](" + prefix + item.path + "#" + getMdLink(item.crude_title) + ")"
            if item.date:
                data.append([entry, "@" + item.date + "<br>" + item.title])
            else:
                data.append([entry, "@" + item.hook + "<br>" + item.title])
        
        while len(data) % posts_per_row != 0:
            if empty_fig != None:
                data.append(["![](" + empty_fig + ")", " "])
            else:
                data.append(["-", "*"])
        
        lines = []
        for i in range(0, len(data), posts_per_row):
            a, b, c = Itens.__makeRow(data[i: i + posts_per_row])
            lines += [a, b, c]
        return "".join(lines)

    def generateView(self, tree, out_file):
        reverse_sort = Item.cfg["extra"]["reverse_sort"]
        view_text = io.StringIO()
        view_text.write("## @qxcode\n\n")
        levels = out_file.split(os.sep)
        prefix = "../" * (len(levels) - 1)

        for key, lista in tree.items():
            view_text.write("\n### " + key + "\n\n")
            lista.sort(key=lambda x: x.getFulltitle(), reverse = reverse_sort)
            text = Itens.__makeTableEntry(lista, prefix)
            view_text.write(text)
        
        with open(out_file, "w") as f:
            f.write(view_text.getvalue())

    # update Readme.md
    def generateIndex(self, tree, out_file):
        summary = io.StringIO()
        readme_text = io.StringIO()
        readme_text.write("## @qxcode\n\n")
        #readme_text.write("## " + "Categorias" + "\n\n")

        levels = out_file.split(os.sep)
        prefix = "../" * (len(levels) - 1)

        for key, lista in tree.items():
            readme_text.write("\n### " + key + "\n\n")
            lista.sort(key=lambda x: x.getFulltitle())
            for item in lista:
                path = (prefix + item.path).replace("/./", "/")
                entry = "- [" + item.title.strip() + "](" + path + "#" + getMdLink(item.crude_title) + ")\n"
                readme_text.write(entry)
        
        with open(out_file, "w") as f:
            f.write(readme_text.getvalue())

    def generateSummary(self, tree, out_file):
        summary = io.StringIO()
        for key, lista in tree.items():
            summary.write("#" + key + "\n")
            for item in lista:
                vet = item.path.split(os.sep)
                summary.write(vet[-2] + " ")
            summary.write("\n\n")
        with open(out_file, "w") as f:
            f.write(summary.getvalue())
        summary.close()

    def __str__(self):
        return "\n".join(str(v) for v in self.itens)

    def generate_thumbs(self):
        thumbs_dir = Itens.cfg["thumbs"]
        if not os.path.isdir(thumbs_dir):
            os.makedirs(thumbs_dir)
        self.itens.sort(key = lambda x: x.path)
        for item in self.itens:
            item.makeThumb()


def main():
    parser = argparse.ArgumentParser(prog='indexer.py')
    parser.add_argument('-s', action='store_true', help='set titles using names.txt')
    parser.add_argument('-r', action='store_true', help='rebuild thumbs')
    args = parser.parse_args()

    cfg = loadConfig()
    Item.cfg = cfg
    Itens.cfg = cfg

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

    if not os.path.exists(cfg["config"]):
        os.mkdir(cfg["config"])

    if args.r:
        rmtree(cfg["thumbs"], ignore_errors=True)
        os.mkdir(cfg["thumbs"])

    itens.generateBoard()
    cat_tree = itens.tree_generate_cat()
    tag_tree = itens.tree_generate_tag()
    if cfg["links"]:
        itens.generateLinks()
    if cfg["tag"]["view"] or cfg["cat"]["view"]:
        itens.generate_thumbs()
        
    if cfg["cat"]["index"]:
        itens.generateIndex(cat_tree, cfg["cat"]["index"])
    if cfg["cat"]["summary"]:
        itens.generateSummary(cat_tree, cfg["cat"]["summary"])
    if cfg["cat"]["view"]:
        itens.generateView(cat_tree, cfg["cat"]["view"])
    
    if cfg["tag"]["index"]:
        itens.generateIndex(tag_tree, cfg["tag"]["index"])
    if cfg["tag"]["summary"]:
        itens.generateSummary(tag_tree, cfg["tag"]["summary"])
    if cfg["tag"]["view"]:
        itens.generateView(tag_tree, cfg["tag"]["view"])

    print("all done")


if __name__ == '__main__':
    main()
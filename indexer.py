#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import argparse
import re
import subprocess
import csv
import io
from shutil import rmtree
from typing import Dict, List, Tuple, Union, Any, Callable


class Util:

    @staticmethod
    def join(path_list           )       :
        path_list = [os.path.normpath(x) for x in path_list]
        path = ""
        for x in path_list:
            path = os.path.join(path, x)
        return os.path.normpath(path)

    @staticmethod
    def normpath(file     )       :
        return os.path.normpath(file)

    @staticmethod
    def extract_title_content(line                  )       :
        if line is None or len(line) == 0:
            return ""
        if line[-1] == "\n":
            line = line[:-1]
        words = line.split(" ")
        if Util.only_hashtags(words[0]):
            return " ".join(words[1:])
        return " ".join(words)

    @staticmethod
    def get_directions(source     , destination     )       :
        if source == '.' or source == './':
            return destination
        return Util.join(["../" * (len(source.split(os.sep)) - 1), destination])

    @staticmethod
    def split_path(path     )                   :
        path = Util.normpath(path)
        vet = path.split(os.path.sep)
        if len(vet) == 1:
            return ".", path
        return os.sep.join(vet[0:-1]), vet[-1]

    @staticmethod
    def create_dirs_if_needed(path     )        :
        root, file = Util.split_path(path)
        if not os.path.isdir(root):
            os.makedirs(root)

    @staticmethod
    def get_md_link(title                  )       :
        if title is None:
            return ""
        title = Util.extract_title_content(title)
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

    @staticmethod
    def only_hashtags(x     )        : return len(x) == x.count("#")

    @staticmethod
    def split_list(l           , p     )                               :
        return [x[1:] for x in l if x.startswith(p)], [x for x in l if not x.startswith(p)]

    @staticmethod
    def get_first(info_list           )       : return info_list[0] if len(info_list) > 0 else None

#    @staticmethod
#    def sort_keys_lambda(keys, group_by, labels):
#        if(group_by == "categories"):
#            return sorted(keys, key=lambda x: labels.get_index(x))
#        return sorted(keys)

    @staticmethod
    def get_key_name(key, group_by, labels):
        if(group_by == "categories"):
            return labels.get_label(key).label
        return key


class Config:
    @staticmethod
    def get_default_cfg():
        cfg = {
            "execute": [
                {
                    "action": "run",
                    "cmds": [
                        ["cmd", "arg", "arg"],
                        ["cmd", "arg", "arg"]
                    ]
                },
                {
                    "action": "load_folder",
                    "dir": "base"
                },
                {
                    "action": "board", 
                    "file": ".indexer/board.md"
                },
                {
                    "action": "links",
                    "dir": ".indexer/links"
                },
                {
                    "action": "thumbs", 
                    "width": 320,
                    "height": 180
                },
                {
                    "action": "index", 
                    "intro": None,
                    "file": ".indexer/cat_index.md",
                    "group_by": "categories",
                    "reverse_sort": False
                },
                {
                    "action": "view", 
                    "intro": None,
                    "file": ".indexer/cat_view.md",
                    "group_by": "categories",
                    "posts_per_row": 3,
                    "empty_fig": None
                },
                {
                    "action": "posts",
                    "dir": "_posts",
                    "base_raw_remote": "https://raw.githubusercontent.com/senapk/senapk.github.io/master/base",
                    "default_date": None,
                    "categories_dir": "category"
                }
            ]
        }
        return cfg

    @staticmethod
    def get_default_symbols():
        symbols = {
            "tag": "#",
            "category": "\u00a9",
            "date": "\u00f0",
            "author": "\u00e6",
            "order": "dcTta"
        }
        return symbols

    @staticmethod
    def load_cfg(config_file):
        if not os.path.isfile(config_file):
            print("  fail: create a " + config_file + "like in https://github.com/senapk/indexer")
            exit(1)
        with open(config_file, "r") as f:
            cfg = json.load(f)
            keys = [x for x in Config.get_default_cfg().keys()]
            Config.check_and_merge(cfg, keys)
            return cfg
        
    @staticmethod
    def load_symbols(symbols_file):
        if not os.path.isfile(symbols_file):
            print("  warning: .symbols.json not found in", symbols_file, ", loading default value and creating file")
            symbols = Config.get_default_symbols()
            with open(symbols_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(symbols, indent=2))
            return symbols

        with open(symbols_file, "r") as f:
            symbols = json.load(f)
            print("Loading symbols")
            keys = [x for x in Config.get_default_symbols().keys()]
            Config.check_and_merge(symbols, keys)
            if sorted(symbols["order"]) != sorted(Config.get_default_symbols()["order"]):
                print("  error: symbols key 'order' should be a anagram of 'dcTta'")
                exit(1)
            return symbols

    @staticmethod
    def check_and_merge(received                , needed           , optional                 = None)                  :
        all_keys = needed[:]
        if optional:
            all_keys += [x for x in optional.keys()]
        for opt in received.keys():
            if opt not in all_keys:
                print("  error: config doesn't have the key:", opt)
                print("         the options are", str(all_keys))
                exit(1)
        for opt in needed:
            if opt not in received.keys():
                print("  error: config requires the key:", opt)
                print("         the options required are", str(needed))
                exit(1)
        if optional:
            optional.update(received)
            return optional
        return received


class Item:
    @staticmethod
    def normalize_file(readme_path):
        with open(readme_path, "r") as f:
            lines = f.readlines()
            fulltext = "".join(lines)

        if len(lines) == 0:
            print("  warning: filling empty on ", readme_path)
            lines.append("# Empty #empty\n")
            lines.append("\n")

        if len(lines) == 1:
            lines.append("\n")

        for i in range(len(lines)):
            if lines[i] == "" or lines[i][-1] != "\n":
                lines[i] = lines[i] + "\n"

        if fulltext != "".join(lines):
            with open(readme_path, "w") as f:
                f.write("".join(lines))

        return lines[0][:-1], lines[1][:-1], "".join(lines[2:])

    def __init__(self, symbols, path):
        self.symbols = symbols
        crude_title, self.description, self.content = Item.normalize_file(path)
        self.__parse_title(crude_title)
        self.path_full = Util.normpath(path)                               # arcade/base/000/Readme.md
        self.base = os.sep.join(self.path_full.split(os.sep)[:-2])         # arcade/base
        self.hook = path.split(os.sep)[-2]                                 # 000
        self.filename = path.split(os.sep)[-1]                             # Readme.md
        self.cover = self.__get_cover()                                    # cover.jpg ou ../001/cover.jpg
        self.fulltitle = self.__sort_fulltitle()                           # first line content withoub the \n
        if crude_title != self.fulltitle:
            with open(path, "w") as f:
                f.write(self.fulltitle + "\n" + self.content)

    def __parse_title(self, first_line):
        symbols = self.symbols
        words = first_line.split(" ")
        self.level = None
        if Util.only_hashtags(words[0]):
            self.level = words[0]
            del words[0]
        words = [x for x in words if not Util.only_hashtags(x)]
        self.tags, words = Util.split_list(words, symbols["tag"])
        self.categories, words = Util.split_list(words, symbols["category"])
        self.authors, words = Util.split_list(words, symbols["author"])
        self.date, words = Util.split_list(words, symbols["date"])
        self.title = " ".join(words).strip() if len(words) > 0 else ''
        self.date = Util.get_first(self.date)
        if len(self.categories) == 0:
            self.categories.append(Label.ORPHAN)
        if len(self.tags) == 0:
            self.tags.append(Label.ORPHAN)
        if len(self.authors) == 0:
            self.authors.append(Label.ORPHAN)
        # self.category = util.get_first(category_key)
        # self.author = util.get_first(self.author)
        # self.category = Category.get_category(cat_dict, category_key)
        # Category.count_item(cat_dict, category_key)

    def __get_cover(self):
        regex = r"!\[(.*?)\]\(([^:]*?)\)"
        match = re.search(regex, self.content)
        if match:
            img = os.path.normpath(match.group(2))  # cover.jpg
            if not os.path.isfile(Util.join([self.base, self.hook, img])):
                print("  error: cover image not found in ", self.path_full)
                exit(1)
            return img
        return None

    def __sort_fulltitle(self):
        symbols = self.symbols
        out = []
        if self.level:
            out += [self.level]
        for s in symbols["order"]:
            if s == 'd':
                if self.date:
                    out += [symbols["date"] + self.date]
            if s == 'c':
                for cat in self.categories:
                    if cat != Label.ORPHAN:
                        out += [symbols["category"] + cat]
            if s == 'T':
                if self.title:
                    out += [self.title]
            if s == 't':
                for tag in self.tags:
                    if tag != Label.ORPHAN:
                        out += [symbols["tag"] + tag]
            if s == 'a':
                for author in self.authors:
                    if author != Label.ORPHAN:
                        out += [symbols["author"] + author]
        return " ".join(out)

    def __str__(self):
        return self.__sort_fulltitle()


class Label:
    ORPHAN = "__orphan__"
    @staticmethod
    def create_by_key(key     ):
        return Label(100, key, key, key)

    def __init__(self, index=0, key="", label="", description=""):
        self.index      = index
        self.key      = key
        self.label      = label
        self.description      = description

    def __lt__(self, other):
        return self.index < other.index

    def __str__(self):
        return self.label


class LabelRepository:
    def __init__(self, source     ):
        self.source      = source
        self.labels                   = {}
        self.__load_from_file()

    def get_label(self, key                  )         :
        if key is None:
            key = Label.ORPHAN
        if key in self.labels:
            return self.labels[key]
        self.labels[key] = Label.create_by_key(key)
        return self.labels[key]

    def get_index(self, key     )       :
        return self.get_label(key).index

    def check(self, key     )        :
        if key not in self.labels:
            self.labels[key] = Label.create_by_key(key)

    def __load_from_file(self)        :
        if os.path.isfile(self.source):
            with open(self.source, 'r') as f:
                spam = csv.reader(f, delimiter=',', quotechar='"', skipinitialspace=True)
                index = 0
                for row in spam:
                    key, label, description = row[1:]
                    self.labels[key] = Label(index, key, label, description)
                    index += 1

    def save_on_file(self, item_list            ):
        qtds                 = {}
        for item in item_list:
            for cat in item.categories:
                if cat not in qtds:
                    qtds[cat] = 1
                else:
                    qtds[cat] += 1
                self.check(cat)  # inserindo as chaves que tem nos itens e faltam nos labels
        for key in self.labels.keys():
            if key not in qtds:
                qtds[key] = 0

        with open(self.source, "w") as out:
            write = csv.writer(out, delimiter=',', quotechar='"')
            for x in sorted(self.labels.values()):  # ordena pelo indice
                write.writerow([qtds[x.key], x.key, x.label, x.description])


class Sorter:
    @staticmethod
    def test_key(item      , key     ):
        if not hasattr(item, key):
            print("    fail: Item doesn't have the key", key)
            print("    The options are ", ["title", "fulltitle", "hook", "categories", "tags", "authors", "path_full"])
            exit(1)

    @staticmethod
    def sorted_by_key(itens            , labels                 , key     , reverse       = False)              :
        if len(itens) == 0:
            return []
        Sorter.test_key(itens[0], key)
        if type(getattr(itens[0], key)) is list:
            if key == "categories":
                return sorted(itens, key=lambda x: labels.get_index(getattr(x, key)[0]), reverse=reverse)
            else:
                return sorted(itens, key=lambda x: getattr(x, key)[0], reverse=reverse)
        return sorted(itens, key=lambda x: getattr(x, key), reverse=reverse)

    @staticmethod
    def group_by(itens            , labels                 , group_by, reverse_sort)                                :
        tree = {}
        if len(itens) > 0:
            Sorter.test_key(itens[0], group_by)
        for item in itens:
            data = getattr(item, group_by)
            if data is None:
                data = []
            elif not type(data) is list:
                data = [data]

            if len(data) == 0:
                if Label.ORPHAN not in tree:
                    tree[Label.ORPHAN] = []
                tree[Label.ORPHAN].append(item)
            else:
                for elem in data:
                    if elem not in tree:
                        tree[elem] = []
                    tree[elem].append(item)
        output                               = []

        for key in tree.keys():
            tree[key].sort(key=lambda x: x.fulltitle)
            output.append([key, tree[key]])
        if group_by == "categories":
            output.sort(key=lambda x: labels.get_index(x[0]), reverse=reverse_sort)
        else:
            output.sort(key=lambda x: x[0], reverse=reverse_sort)
        return output


class ItemRepository:
    def __init__(self, base     ):
        self.base = os.path.normpath(base)
        self.__test_exists()
        self.itens             = []
        self.symbols                 = Config.load_symbols(self.get_symbols_file_path())
        self.load_itens()
        self.cat_labels = LabelRepository(self.get_categories_file_path())
        self.cat_labels.save_on_file(self.itens)
        self.cats = Sorter.group_by(self.itens, self.cat_labels, "categories", False)

    def __test_exists(self):
        if not os.path.isdir(self.base):
            print("  error: base dir is missing")
            exit(1)

    def get_categories_file_path(self):
        return Util.join([self.base, ".categories.csv"])

    def get_symbols_file_path(self):
        return Util.join([self.base, ".symbols.json"])

    def load_itens(self):
        for (root, _dirs, files) in os.walk(self.base, topdown=True):
            folder = root.split(os.sep)[-1]
            if folder.startswith("_") or folder.startswith("."):
                continue
            if root.count(os.sep) - self.base.count(os.sep) != 1:  # one level only
                continue
            files = [x for x in files if x.endswith(".md")]
            for file in files:
                if file.startswith("_") or file.startswith(">"):
                    continue
                path = Util.join([root, file])
                self.itens.append(Item(self.symbols, path))


class Board:
    @staticmethod
    def get_entry(item, board_file):
        return "[](" + Util.get_directions(board_file, item.path_full) + ')', item.fulltitle, item.description

    @staticmethod
    def update_titles(board_file):
        f = open(board_file, "r")
        names_list = [x for x in f.readlines() if x != "\n"]
        f.close()
        for line in names_list:
            parts = line.split(":")
            path = parts[0].strip()[3:-1]  # removing []( )
            fulltitle = parts[1].strip()
            description = parts[2].strip()
            
            vet = path.split(os.sep)
            filename = vet[-1]
            hook = vet[-2]
            base = vet[-3] if len(vet) > 2 else ""
            path = Util.join([base, hook, filename])

            if not os.path.isfile(path):
                Util.create_dirs_if_needed(path)
                print("  warning: file", path, "not found, creating!")
                with open(path, "w") as f:
                    f.write(fulltitle + " #empty\n")
                    f.write(description + "\n")
            else:
                with open(path, "r") as f:  # updating first line content
                    data = f.readlines()
                old_first_line = data[0] if len(data) > 0 else ""
                new_first_line = fulltitle + "\n"
                old_description = data[1] if len(data) > 1 else ""
                new_description = description + "\n"
                if old_first_line != new_first_line or old_description != new_description:
                    with open(path, "w") as f:
                        content = "".join(data[2:]) if len(data) > 2 else ""
                        f.write(new_first_line + new_description + content)

    @staticmethod
    def generate(item_rep                , board_file     , sort_by     , reverse_sort      ):
        groups = Sorter.group_by(item_rep.itens, item_rep.cat_labels, sort_by, reverse_sort)
        itens = []
        for _key, item_list in groups:
            itens += item_list

        paths = []
        full_titles = []
        subtitles = []
        max_len_path = 0
        max_len_title = 0
        for x in itens:
            path, fulltitle, subtitle = Board.get_entry(x, board_file)
            if len(path) > max_len_path:
                max_len_path = len(path)
            if len(fulltitle) > max_len_title:
                max_len_title = len(fulltitle)
            paths.append(path)
            full_titles.append(fulltitle)
            subtitles.append(subtitle if subtitle is not None else "")
        paths = [x.ljust(max_len_path) for x in paths]
        full_titles = [x.ljust(max_len_title) for x in full_titles]
        Util.create_dirs_if_needed(board_file)
        with open(board_file, "w") as names:
            for i in range(len(paths)):
                names.write(paths[i] + " : " + full_titles[i] + " : " + subtitles[i] + "\n")


class Links:
    @staticmethod
    def generate(item_rep                , links_dir     ):
        if os.path.isdir(links_dir):
            rmtree(links_dir, ignore_errors=True)
        if not os.path.isdir(links_dir):
            os.makedirs(links_dir)
        for item in item_rep.itens:
            path = Util.join([links_dir, item.title.strip() + ".md"])
            with open(path, "w") as f:
                f.write("[LINK](" + Util.get_directions(path, item.path_full) + ")\n")


class Index:
    @staticmethod
    def generate(item_rep                , out_file, group_by, reverse_sort)       :
        groups = Sorter.group_by(item_rep.itens, item_rep.cat_labels, group_by, reverse_sort)
        output = io.StringIO()
        output.write("\n## Links\n")
        for key, _item_list in groups:
            label = Util.get_key_name(key, group_by, item_rep.cat_labels)
            link = Util.get_md_link(label)
            output.write("- [" + label + "](#" + link + ")\n")
        for key, item_list in groups:
            output.write("\n## " + Util.get_key_name(key, group_by, item_rep.cat_labels) + "\n\n")
            for item in item_list:
                item_path = item.path_full + "#" + Util.get_md_link(item.fulltitle)
                entry = "- [" + item.title.strip() + "](" + Util.get_directions(out_file, item_path) + ")\n"
                output.write(entry)
        return output.getvalue()


class Summary:
    @staticmethod
    def generate(item_rep                , group_by     ):
        groups = Sorter.group_by(item_rep.itens, item_rep.cat_labels, group_by, False)
        output = io.StringIO()
        for key, item_list in groups:
            output.write("\n## " + Util.get_key_name(key, group_by, item_rep.cat_labels) + "\n\n")
            for item in item_list:
                output.write(item.hook + " ")
            output.write("\n\n")
        return output.getvalue()


class View:
    @staticmethod
    def __make_row(data                 ):
        a = "|".join([x[0] for x in data]) + "\n"
        b = "|".join(["-"] * len(data)) + "\n"
        c = "|".join([x[1] for x in data]) + "\n\n\n"
        return a, b, c

    @staticmethod
    def __make_table_entry(item_list            , out_file     , empty_fig     , posts_per_row     ):
        data = []
        for item in item_list:
            thumb = Thumbs.get_thumb_full(item)
            if thumb:
                thumb = Util.get_directions(out_file, thumb)
            else:
                if empty_fig:
                    thumb = Util.get_directions(out_file, empty_fig)
                else:
                    thumb = "https://placekitten.com/320/181"
            file_path = Util.get_directions(out_file, item.path_full + "#" + Util.get_md_link(item.fulltitle))
            entry = "[![](" + thumb + ")](" + file_path + ")"
            if item.date:
                data.append([entry, "@" + item.date + "<br>" + item.title])
            else:
                data.append([entry, "@" + item.hook + "<br>" + item.title])

        while len(data) % posts_per_row != 0:
            if empty_fig:
                data.append(["![](" + empty_fig + ")", " "])
            else:
                data.append(["-", "*"])

        lines = []
        for i in range(0, len(data), posts_per_row):
            a, b, c = View.__make_row(data[i: i + posts_per_row])
            lines += [a, b, c]
        return "".join(lines)

    @staticmethod
    def generate( item_rep               , out_file, group_by, reverse_sort, empty_fig     , posts_per_row     ):
        groups = Sorter.group_by(item_rep.itens, item_rep.cat_labels, group_by, reverse_sort)
        output = io.StringIO()
        output.write("\n## Links\n")
        for key, _item_list in groups:
            label = Util.get_key_name(key, group_by, item_rep.cat_labels)
            link = Util.get_md_link(label)
            output.write("- [" + label + "](#" + link + ")\n")
        for key, item_list in groups:
            output.write("\n## " + Util.get_key_name(key, group_by, item_rep.cat_labels) + "\n\n")
            text = View.__make_table_entry(item_list, out_file, empty_fig, posts_per_row)
            output.write(text)
        return output.getvalue()


class Thumbs:
    @staticmethod
    def generate(item_rep                , width     , height     , rebuild_all      ):
        itens = sorted(item_rep.itens, key=lambda x: x.hook)
        for item in itens:
            Thumbs.make(item, width, height, rebuild_all)

    # return .thumb/hook/Readme.jpg
    @staticmethod
    def get_thumb(item      )                    :
        if item.cover:
            return Util.join([".thumb", item.hook, item.filename[:-2] + "jpg"])
        return None

    # return "arcade/base/.thumb/hook/Readme.jpg"
    @staticmethod
    def get_thumb_full(item      ):
        if item.cover:
            return Util.join([item.base, Thumbs.get_thumb(item)])
        return None

    @staticmethod
    def make(item      , width     , height     , rebuild_all      ):
        thumb_full = Thumbs.get_thumb_full(item)
        if thumb_full is None:
            print("  warning: thumb skipping, missing cover on", item.path_full)
            return
        cover_full = Util.join([item.base, item.hook, item.cover])
        Util.create_dirs_if_needed(thumb_full)
        if rebuild_all or not os.path.isfile(thumb_full) or os.path.getmtime(cover_full) > os.path.getmtime(thumb_full):
            print("  making thumb for", item.path_full)
            cmd = ['convert', cover_full, '-resize', str(width) + 'x' + str(height) + '>', thumb_full]
            subprocess.run(cmd)


class Posts:
    @staticmethod
    def write_post(item      , cat_labels                 , posts_dir     , default_date                  , remote):
        if item.date is None and default_date is None:
            print("  warning: Date missing, using on", item.path_full, ", skipping")
            return
        if item.date is None:
            item.date = default_date
        if item.cover is None:
            print("  warning: Cover missing, skip", item.path_full)
            return
        if remote[-1] == "/":
            remote = remote[:-1]
        out = io.StringIO()
        out.write("---\nlayout: post\n")
        out.write("title: " + item.title + '\n')
        out.write("image: " + remote + "/" + item.hook + "/" + item.cover + "\n")
        out.write("optimized_image: " + remote + "/" + Thumbs.get_thumb(item) + "\n")
        if item.description:
            description = Util.extract_title_content(item.description)
            out.write("subtitle: " + description + "\n")
            out.write("description: " + description + "\n")

        category = cat_labels.get_label(item.categories[0])
        out.write("category: " + category.key + "\n")
        if Label.ORPHAN not in item.tags:
            out.write("tags:\n")
            for t in item.tags:
                out.write("  - " + t + "\n")
        for author in item.authors:
            if author != Label.ORPHAN:
                out.write("author: " + author + "\n")
        out.write("---\n")
        warning_msg = "<!-- DON'T EDIT THIS FILE, GENERATED BY SCRIPT -->\n" * 5
        out.write(warning_msg)
        out.write(item.content)
        out.write(Posts.get_tests_link(item))
        text = out.getvalue()

        regex = r"\[(.*?)\]\(([^:]*?)\)"
        text = re.sub("!" + regex, "", text, 1, re.MULTILINE)  # removing cover
        subst = "[\\1](" + remote + "/" + item.hook + "/" + "\\2)"
        text = re.sub(regex, subst, text, 0, re.MULTILINE)  # creating full url for links

        regex = r"<img src=\"([^:]*?)\""
        subst = '<img src=\"' + remote + "/" + item.hook + "/" + "\\1" + '\"'
        text = re.sub(regex, subst, text, 0, re.MULTILINE)

        name = "%s-c%02d-%s-%s" % (item.date, category.index, category.key, item.title)
        name = Util.get_md_link(name) + "-@" + item.hook + ".md"
        while "--" in name:
            name = name.replace("--", "-")
        with open(posts_dir + os.sep + name, "w") as f:
            f.write(text)

    @staticmethod
    def get_tests_link(item      ):
        out = io.StringIO()
        out.write("\n## Tests\n")
        test_path = Util.join([item.base, item.hook, "t.tio"])
        if os.path.isfile(test_path):
            out.write("[DONWLOAD](t.tio)\n\n")
            return out.getvalue()
        return ""

    @staticmethod 
    def find_old_posts(item      , posts_dir     ):
        files = os.listdir(posts_dir)
        files = [Util.join([posts_dir, x]) for x in files]
        files = [x for x in files if os.path.isfile(x)]
        files = [x for x in files if x.endswith("-@" + item.hook + ".md")]
        return files

    # return if content is new
    @staticmethod
    def is_new_content(item      , posts_dir     , rebuild_all      ):
        files = Posts.find_old_posts(item, posts_dir)
        if len(files) == 0:
            return True
        is_new = False
        for file in files:
            if rebuild_all or os.path.getmtime(item.path_full) > os.path.getmtime(file):
                print("  replacing post", file)
                os.remove(file)
                is_new = True
        return is_new

    @staticmethod
    def generate(item_rep                , posts_dir     , default_date                  , remote     ,
                 categories_dir     , file_linker     , rebuild_all      ):
        for item in item_rep.itens:
            Posts.is_new_content(item, posts_dir, rebuild_all)
            Posts.write_post(item, item_rep.cat_labels, posts_dir, default_date, remote)
        Posts.generate_categories_files(item_rep, categories_dir, file_linker)

    @staticmethod
    def generate_categories_files(item_rep                , categories_dir     , file_linker     ):
        categories_dir = os.path.normpath(categories_dir)
        rmtree(categories_dir, ignore_errors=True)
        os.mkdir(categories_dir)
        link_entries = []
        for key, itens in item_rep.cats:
            cat = item_rep.cat_labels.get_label(key)
            if len(itens) > 0:
                link_entries.append('<li><a href="/category/' + cat.key + '">{{ "' + cat.label + '" }}</a></li>\n')
                with open(Util.join([categories_dir, cat.key + ".md"]), "w") as f:
                    f.write("---\n")
                    f.write("layout: category\n")
                    f.write("title: " + cat.label + "\n")
                    f.write("slug: " + cat.key + "\n")
                    f.write("description: " + cat.description + "\n")
                    f.write("---\n")

        if file_linker:
            text = open(file_linker, "r").read()
            regex = r"<!--BEGIN-->\n(.*?)^\s*<!--END-->"
            subst = "<!--BEGIN-->\\n" + "".join(link_entries) +  "<!--END-->"
            text = re.sub(regex, subst, text, 0, re.MULTILINE | re.DOTALL)
            open(file_linker, "w").write(text)


class Main:
    #ctions: Dict[str, Callable[[ItemRepository, Dict[str, Any], Any], ItemRepository]]

    def __init__(self):
        self.actions = {}
        self.load_modules()

    def add_action(self, key     , fn                                                                 )        :
        self.actions[key] = fn

    @staticmethod
    def init_json():
        f = open(".indexer.json", "w")
        print("Creating .indexer.json file")
        f.write(json.dumps(Config.get_default_cfg(), indent=2))
        f.close()
        exit(0)

    @staticmethod
    def update_from_board(board):
        if board:
            print("Updating names using board")
            Board.update_titles(board)

    @staticmethod
    def save_file(intro, out_file, text):
        out_file = os.path.normpath(out_file)
        if intro:
            intro = os.path.normpath(intro)
            if not os.path.isfile(intro):
                print("  fail: file", intro, "not found")
                exit(1)
            with open(out_file, "w") as f:
                f.write(open(intro, "r").read())
                f.write(text)
        else:
            with open(out_file, "w") as f:
                f.write(text)

    def load_modules(self):
        def load_folder(_item_rep, options, _args):
            print("Loading folder")
            Config.check_and_merge(options, ["action", "dir"])
            item_rep = ItemRepository(options["dir"])
            return item_rep
        self.add_action("load_folder", load_folder)

        def make_board(item_rep, options, _args):
            print("Generating board")
            optional = {"sort_by": "categories", "reverse_sort": False}
            op = Config.check_and_merge(options, ["action", "file"], optional)
            Board.generate(item_rep, op["file"], op["sort_by"], op["reverse_sort"])
            return item_rep
        self.add_action("board", make_board)

        def run_scripts(item_rep, options, _args):
            print("Running Scripts")
            Config.check_and_merge(options, ["action", "cmds"])
            for cmd in options["cmds"]:
                print(cmd)
                print("$ " + " ".join(cmd))
                subprocess.run(cmd)
            return item_rep
        self.add_action("run", run_scripts)

        def make_thumbs(item_rep, options, args):
            print("Generating thumbs")
            Config.check_and_merge(options, ["action", "width", "height"])
            Thumbs.generate(item_rep, int(options["width"]), int(options["height"]), args.r)
            return item_rep
        self.add_action("thumbs", make_thumbs)

        def make_links(item_rep, options, _args):
            print("Generating links")
            Config.check_and_merge(options, ["action", "dir"])
            Links.generate(item_rep, options["dir"])
            return item_rep
        self.add_action("links", make_links)

        def make_index(item_rep, options, _args):
            print("Generating index")
            default = {"intro": None, "reverse_sort": False, "group_by": "categories"}
            op = Config.check_and_merge(options, ["action", "file"], default)
            text = Index.generate(item_rep, op["file"], op["group_by"], op["reverse_sort"])
            Main.save_file(op["intro"], op["file"], text)
            return item_rep
        self.add_action("index", make_index)

        def make_summary(item_rep, options, _args):
            print("Generating summary")
            default = {"intro": None, "group_by": "categories"}
            op = Config.check_and_merge(options, ["action", "file"], default)
            text = Summary.generate(item_rep, op["group_by"])
            Main.save_file(op["intro"], op["file"], text)
            return item_rep
        self.add_action("summary", make_summary)

        def make_view(item_rep, options, _args):
            print("Generating photo board")
            d = {"intro": None, "group_by": "categories", "reverse_sort": False,
                 "posts_per_row": 4, "empty_fig": None}
            op = Config.check_and_merge(options, ["action", "file"], d)
            text = View.generate(item_rep, op["file"], op["group_by"], op["reverse_sort"], op["empty_fig"],
                                 op["posts_per_row"])
            Main.save_file(op["intro"], op["file"], text)
            return item_rep
        self.add_action("view", make_view)
        
        def make_posts(item_rep, options, args):
            print("Generating posts")
            default = {"default_date": None}
            op = Config.check_and_merge(options, ["action", "dir", "default_date", "base_raw_remote", "categories_dir",
                                                  "file_linker"], default)
            posts_dir = op["dir"]
            date = op["default_date"]
            remote = op["base_raw_remote"]
            categories_dir = op["categories_dir"]
            file_linker = op["file_linker"]
            Posts.generate(item_rep, posts_dir, date, remote, categories_dir, file_linker, args.r)
            return item_rep
        self.add_action("posts", make_posts)

    def execute_actions(self, options                , item_rep                , args):
        for key in self.actions:
            if key == options["action"]:
                item_rep = self.actions[key](item_rep, options, args)
                return item_rep

        print("  error: action", options["action"], "not found")
        print("  you need choose one of this actions:")
        print("  ", self.actions.keys())


def main():
    parser = argparse.ArgumentParser(prog='indexer.py')
    parser.add_argument('-b', action='store', help='set titles using board')
    parser.add_argument('-r', action='store_true', help='rebuild all')
    parser.add_argument('--init', action='store_true', help='show .indexer.json default')
    args = parser.parse_args()

    indexer = Main()
    if args.init:
        indexer.init_json()

    cfg = Config.load_cfg(".indexer.json")
    Config.check_and_merge(cfg, ["execute"])
    if args.b:
        indexer.update_from_board(args.b)
    item_rep = None
    for options in cfg["execute"]:
        item_rep = indexer.execute_actions(options, item_rep, args)
        
    print("All done!")


if __name__ == '__main__':
    main()

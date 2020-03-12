import pynvim
import requests
import re
import time
import yaml
from pathlib import Path
import os

@pynvim.plugin
class Main(object):
    def __init__(self, vim):
        self.vim = vim
        self.bufferName = 'nvim-gist'

    @pynvim.function('GistFetch')
    def GistFetch(self, args):
        auth_config = self.get_auth_config()

        line = self.vim.current.line
        gistId = re.search('gist:\s(.*)\s.*', line).group(1)

        self.vim.command('echon "Fetching ' + gistId + '"')

        response = requests.get('https://api.github.com/gists/' + gistId, auth=(auth_config["username"], auth_config["token"]))
        gist = response.json()

        self.vim.command('echon "Done Fetching ' + gistId + '"')

        filename = list(gist["files"].keys())[0]

        content = gist["files"][filename]["content"]

        self.close_existing_buffers()

        self.vim.command('silent noautocmd new')

        self.detect_syntax(filename)

        self.vim.funcs.execute('noautocmd file gist:' + gistId + '/' + filename)

        self.vim.funcs.setline(1, content.split('\n'))

        self.vim.command('setlocal buftype=acwrite bufhidden=hide noswapfile')
        self.vim.command('setlocal nomodified')

        self.vim.command('echo ""')

        # TODO: Find a better way to define this autocommand
        self.vim.command('au! BufWriteCmd <buffer> call GistSave("' + gistId +'" , "' + filename +'")')

    @pynvim.function('GistSave')
    def GistSave(self, args):
        auth_config = self.get_auth_config()

        self.vim.command('echo "Updating gist..."')

        content = '\n'.join(self.vim.funcs.getline(1, '$'))
        payload = {
                "files" : {
                    args[1]: {
                        "content": content
                        }
                    }
                }

        requests.patch(
            'https://api.github.com/gists/' + args[0],
            json=payload,
            auth=(auth_config["username"], auth_config["token"])
        )

        self.vim.command('setlocal nomodified')
        self.vim.command('echo ""')

    @pynvim.command('GistCreate')
    def GistCreate(self):
        auth_config = self.get_auth_config()

        parse_buffer_name = re.search('gist:(.*)\/(.*)', self.vim.current.buffer.name)

        if parse_buffer_name:
            gist_id = parse_buffer_name.group(1)
            filename = parse_buffer_name.group(2)

            self.GistSave([gist_id, filename])
        else:
            content = '\n'.join(self.vim.funcs.getline(1, '$'))

            self.vim.command('call inputsave()')
            self.vim.command("let nvim_gist_filename = input('Enter the filename: ')")
            self.vim.command('call inputrestore()')

            self.vim.command('echo "Creating gist..."')

            payload = {
                "files" : {
                    self.vim.vars["nvim_gist_filename"]: {
                        "content": content
                        }
                    }
                }

            response = requests.post(
                'https://api.github.com/gists',
                json=payload,
                auth=(auth_config["username"], auth_config["token"])
            )
            gist = response.json()

            self.vim.funcs.execute('noautocmd file gist:' + gist["id"] + '/' + self.vim.vars["nvim_gist_filename"])

            self.vim.command('setlocal buftype=acwrite bufhidden=hide noswapfile')
            self.vim.command('setlocal nomodified')

            self.vim.command('echo ""')

            # TODO: Find a better way to define this autocommand
            self.vim.command('au! BufWriteCmd <buffer> call GistSave("' + gist["id"] +'" , "' + self.vim.vars["nvim_gist_filename"] +'")')

    @pynvim.command('GistList')
    def GistList(self):
        self.vim.command('echo "Listing gists..."')

        auth_config = self.get_auth_config()

        try:
            response = requests.get('https://api.github.com/gists', auth=(auth_config["username"], auth_config["token"]))
        except requests.exceptions.RequestException:
            self.vim.command('echo "Failed to connect to Github"')
            return

        gists = response.json()

        self.close_existing_buffers()

        self.vim.command('silent noautocmd split ' + self.bufferName)

        content = []

        for gist in gists:
            filename = list(gist["files"].keys())[0]
            content.append("gist: " + gist["id"] + " " + filename)

        self.vim.funcs.setline(1, content)

        self.vim.command('setlocal nomodified')
        self.vim.command('setlocal nomodifiable')
        self.vim.command('nnoremap <silent> <buffer> <esc> :bw<cr>')
        self.vim.command('nnoremap <silent> <buffer> <cr> :call GistFetch()<cr>')
        self.vim.command('syntax match SpecialKey /^gist:/he=e-1')
        self.vim.command('syntax match Title /^gist: \S\+/hs=s+5 contains=ALL')
        self.vim.command('echo ""')

    def get_auth_config(self):
        filepath = str(Path.home()) + "/.nvim-gist.yaml"

        try:
            file = open(filepath)
            return yaml.full_load(file)
        except FileNotFoundError as error:
            file = open(filepath, 'w+')

            self.vim.command('call inputsave()')
            self.vim.command("let nvim_gist_github_username = input('Enter your Github username: ')")
            self.vim.command("let nvim_gist_github_token = input('Enter your Github token: ')")
            self.vim.command('call inputrestore()')

            config = {
                        "username": self.vim.vars["nvim_gist_github_username"],
                        "token": self.vim.vars["nvim_gist_github_token"]
                    }

            # Verify the username and token
            self.vim.command('echon "Verifying your username and token..."')
            response = requests.get('https://api.github.com/gists', auth=(config["username"], config["token"]))

            if response.status_code == 200:
                yaml.dump(config, file)
                return config
            else:
                file.close()
                os.unlink(file.name)

                self.vim.command("let nvim_gist_answer = confirm('Invalid credentials. Do you want to re-enter the details again ?', \"&Yes\n&No\", 1)")

                if self.vim.vars["nvim_gist_answer"] == 1:
                    return self.get_auth_config()

    def close_existing_buffers(self):
        for existingBuffer in self.vim.buffers:
            if existingBuffer.name.find(self.bufferName) != -1 and self.vim.funcs.buflisted(existingBuffer):
                self.vim.command('silent! bd ' + str(existingBuffer.number))

    def detect_syntax(self, filename):
        extension = re.search('\.[0-9a-z]+$', filename).group(0)

        extmap = {
            ".adb": "ada",
            ".ahk": "ahk",
            ".arc": "arc",
            ".as": "actionscript",
            ".asm": "asm",
            ".asp": "asp",
            ".aw": "php",
            ".b": "b",
            ".bat": "bat",
            ".befunge": "befunge",
            ".bmx": "bmx",
            ".boo": "boo",
            ".c-objdump": "c-objdump",
            ".c": "c",
            ".cfg": "cfg",
            ".cfm": "cfm",
            ".ck": "ck",
            ".cl": "cl",
            ".clj": "clj",
            ".cmake": "cmake",
            ".coffee": "coffee",
            ".cpp": "cpp",
            ".cppobjdump": "cppobjdump",
            ".cs": "csharp",
            ".css": "css",
            ".cw": "cw",
            ".d-objdump": "d-objdump",
            ".d": "d",
            ".darcspatch": "darcspatch",
            ".diff": "diff",
            ".duby": "duby",
            ".dylan": "dylan",
            ".e": "e",
            ".ebuild": "ebuild",
            ".eclass": "eclass",
            ".el": "lisp",
            ".erb": "erb",
            ".erl": "erlang",
            ".f90": "f90",
            ".factor": "factor",
            ".feature": "feature",
            ".fs": "fs",
            ".fy": "fy",
            ".go": "go",
            ".groovy": "groovy",
            ".gs": "gs",
            ".gsp": "gsp",
            ".haml": "haml",
            ".hs": "haskell",
            ".html": "html",
            ".hx": "hx",
            ".ik": "ik",
            ".ino": "ino",
            ".io": "io",
            ".j": "j",
            ".java": "java",
            ".js": "javascript",
            ".json": "json",
            ".jsp": "jsp",
            ".kid": "kid",
            ".lhs": "lhs",
            ".lisp": "lisp",
            ".ll": "ll",
            ".lua": "lua",
            ".ly": "ly",
            ".m": "objc",
            ".mak": "mak",
            ".man": "man",
            ".mao": "mao",
            ".matlab": "matlab",
            ".md": "markdown",
            ".minid": "minid",
            ".ml": "ml",
            ".moo": "moo",
            ".mu": "mu",
            ".mustache": "mustache",
            ".mxt": "mxt",
            ".myt": "myt",
            ".n": "n",
            ".nim": "nim",
            ".nu": "nu",
            ".numpy": "numpy",
            ".objdump": "objdump",
            ".ooc": "ooc",
            ".parrot": "parrot",
            ".pas": "pas",
            ".pasm": "pasm",
            ".pd": "pd",
            ".phtml": "phtml",
            ".pir": "pir",
            ".pl": "perl",
            ".po": "po",
            ".py": "python",
            ".pytb": "pytb",
            ".pyx": "pyx",
            ".r": "r",
            ".raw": "raw",
            ".rb": "ruby",
            ".rhtml": "rhtml",
            ".rkt": "rkt",
            ".rs": "rs",
            ".rst": "rst",
            ".s": "s",
            ".sass": "sass",
            ".sc": "sc",
            ".scala": "scala",
            ".scm": "scheme",
            ".scpt": "scpt",
            ".scss": "scss",
            ".self": "self",
            ".sh": "sh",
            ".sml": "sml",
            ".sql": "sql",
            ".st": "smalltalk",
            ".swift": "swift",
            ".tcl": "tcl",
            ".tcsh": "tcsh",
            ".tex": "tex",
            ".textile": "textile",
            ".tpl": "smarty",
            ".twig": "twig",
            ".txt" : "text",
            ".v": "verilog",
            ".vala": "vala",
            ".vb": "vbnet",
            ".vhd": "vhdl",
            ".vim": "vim",
            ".weechatlog": "weechatlog",
            ".xml": "xml",
            ".xq": "xquery",
            ".xs": "xs",
            ".yml": "yaml"
        }

        self.vim.command('silent! setlocal ft=' + extmap[extension])

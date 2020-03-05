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

        self.vim.funcs.execute('noautocmd file gist:' + gistId + '/' + filename)

        self.vim.funcs.setline(1, content.split('\n'))

        self.vim.command('setlocal buftype=acwrite bufhidden=hide noswapfile')
        self.vim.command('setlocal nomodified')

        self.vim.command('echo ""')

        # TODO: Find a better way to define this autocommand
        self.vim.command('au! BufWriteCmd <buffer> call GistWrite("' + gistId +'" , "' + filename +'", "' + gist["description"] + '")')

    @pynvim.function('GistWrite')
    def GistWrite(self, args):
        auth_config = self.get_auth_config()

        self.vim.command('echo "Updating gist..."')

        content = '\n'.join(self.vim.funcs.getline(1, '$'))
        payload = {
                "description": args[2],
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

        self.vim.command('echo ""')

    @pynvim.command('GistCreate')
    def GistCreate(self):
        self.vim.command('echo "Creating gist..."')

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

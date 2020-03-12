# nvim-gist

Neovim plugin for Github Gist https://gist.github.com

This plugin is based on [vim-gist](https://github.com/mattn/vim-gist). It is using the Neovim remote plugin so the API requests are run asynchronously.

# Installation

For [vim-plug](https://github.com/junegunn/vim-plug)

```
Plug 'rudylee/nvim-gist', { 'do': ':UpdateRemotePlugins' }
```

# Setting Up

### Generate Github personal access token

Before you can use this plugin, you need to create a Github personal token so the plugin can create and access your gists.

You can visit [https://github.com/settings/tokens](https://github.com/settings/tokens) to generate a new token. Make sure the token has access to create a gist.

### Add personal access token to the plugin

Run the GistList command in your neovim

```
:GistList
```

When you run the list command for the first time, the plugin will ask you to enter the Github username and personal access token.

# Usage

### List gists

```
:GistList
```

### Save current buffer to Gist

```
:GistCreate
```

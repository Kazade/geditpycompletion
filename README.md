
# GEdit Python Code Completion Plugin

This plugin provides Python code completion for GEdit 3.x. 

## Installation

Copy the .plugin file, and the source folder to ~/.local/share/gedit/plugins 

The plugin can then be enabled from the plugin manager. 

## Features

* Currently only parses the current file
* Attempts to guess the type of a variable from assignment statement
* Correctly code completes self. in class methods

## TODO

* Handle tuple assignments
* Copy the scope from the source to the destination during an assignment
* Store a list of types that a variable has been assigned ( e.g a = 1; a = "abc"; should store both IntScope and StrScope on the variable)
* Handle inherited scopes from base classes
* Handle imports
* Handle multiple files, follow and parse unopened imports in a background thread and store the module scope

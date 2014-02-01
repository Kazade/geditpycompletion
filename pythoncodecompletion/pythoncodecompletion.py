# Copyright (C) 2006-2007 Osmo Salomaa
# Copyright (C) 2008 Rodrigo Pinheiro Marques de Araujo
# Copyright (C) 2008 Michael Mc Donnell                      
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

from gi.repository import GObject, Gedit, Gtk, GtkSource
import re
from .code_complete import complete

class PythonCompletionProvider(GObject.Object, GtkSource.CompletionProvider):
    __gtype_name__ = 'PythonCompletionProvider'

    re_alpha = re.compile("\w+", re.UNICODE | re.MULTILINE)
    re_non_alpha = re.compile("\W+", re.UNICODE | re.MULTILINE)

    def __init__(self, view):
        GObject.Object.__init__(self)
        self._view = view
        theme = Gtk.IconTheme.get_default()
        self._info_icon = theme.load_icon(Gtk.STOCK_DIALOG_INFO, 16, 0)

    def do_get_name(self):
        return _("Python Code Completion provider")

    def _get_proposals(self, context):
        doc = self._view.get_buffer()
        insert = context.get_iter()
        start = insert.copy()

        while start.backward_char():
            char = start.get_char()
            if not self.re_alpha.match(char) and not char == ".":
                start.forward_char()
                break

        incomplete = doc.get_text(start, insert, True)
        if not incomplete:
            return []
        
        #print("Finding match for: " + incomplete)
        if incomplete.isdigit():
            #print("Result is a digit, ignoring")
            return []
            
        line = insert.get_line()
        #print("... on line: %s" % line)
        completes = complete( doc.get_text(*(list(doc.get_bounds()) + [True])), incomplete, line)
        if not completes:
            return []
            
        if "." in incomplete:
            incompletelist = incomplete.split('.')
            newword = incompletelist[-1]
            completions = list(x['abbr'][len(newword):] for x in completes)
            length = len(newword)
        else:
            completions = list(x['abbr'][len(incomplete):] for x in completes)
            length = len(incomplete)

        result = []        
        for x in completes:
            x['completion'] = x['abbr'][length:]
            
            result.append(GtkSource.CompletionItem.new(x['abbr'], x['abbr'], self._info_icon, x['abbr']))

        return result
    
    def do_populate(self, context):
        #print("provider_populate called")
        proposals = self._get_proposals(context)
        context.add_proposals(self, proposals, True)
        
    def do_match(self, context):
        return context.get_iter().get_buffer().get_mime_type() == 'text/x-python'

    def do_get_priority(self):
        #print("get_priority")
        return 0

GObject.type_register(PythonCompletionProvider)

class CompletionPlugin(GObject.Object, Gedit.WindowActivatable):

    """Complete python code with the tab key."""

    __gtype_name__ = "CompletionPlugin"
    window = GObject.property(type=Gedit.Window)
    
    def __init__(self):
        #print("Constructing plugin")
        
        GObject.Object.__init__(self)
        
        self.completes = None
        self.completions = None
        self.name = "CompletionPlugin"
        self._providers = {}

    def _add_provider(self, view):
        self._providers[view] = PythonCompletionProvider(view)
        view.get_completion().add_provider(self._providers[view])
        
    def _remove_provider(self, view):
        view.get_completion().remove_provider(self._providers[view])        
        del self._providers[view]
    
    def do_activate(self):
        """Activate plugin."""
        #print("Activating plugin")
        
        self._handlers = []
        callback = self.on_tab_added
        handler_id = self.window.connect("tab-added", callback)
        self._handlers.append(handler_id)

        callback = self.on_tab_removed
        handler_id = self.window.connect("tab-removed", callback)
        self._handlers.append(handler_id)
        
        for view in self.window.get_views():
            self._add_provider(view)
            
        #print("Activation complete")

    def do_deactivate(self):
        """Deactivate plugin."""

        for handler_id in self._handlers:
            self.window.disconnect(handler_id)
        self._handlers = None

    def on_tab_added(self, window, tab, data=None):
        """Connect the document and view in tab."""
        self._add_provider(tab.get_view())

    def on_tab_removed(self, window, tab, data=None):
        self._remove_provider(tab.get_view())
        

        

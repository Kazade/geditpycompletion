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


"""Complete python code with Ctrl+Alt+Space key combination."""

from gi.repository import GObject, Gedit, Gtk, Gdk, PeasGtk
import re
from complete import complete
#import configuration
import configurationdialog
import logging

class CompletionWindow(Gtk.Window):

    """Window for displaying a list of completions."""

    def __init__(self, parent, callback):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.store = None
        self.view = None
        self.completions = None
        self.complete_callback = callback
        self.set_transient_for(parent)
        self.set_border_width(1)
        self.text = Gtk.TextView()
        self.text_buffer = Gtk.TextBuffer()
        self.text.set_buffer(self.text_buffer)
        self.text.set_size_request(300, 200)
        self.text.set_sensitive(False)
        self.init_tree_view()
        self.init_frame()
        self.connect('focus-out-event', self.focus_out_event) 
        self.connect('key-press-event', self.key_press_event)
        self.grab_focus()

    
    def key_press_event(self, widget, event):
        if event.keyval == Gtk.keysyms.Escape:
            self.hide()
        elif event.keyval == Gtk.keysyms.BackSpace:
            self.hide()
        elif event.keyval in (Gtk.keysyms.Return, Gtk.keysyms.Tab):
            self.complete()
        elif event.keyval == Gtk.keysyms.Up:
            self.select_previous()
        elif event.keyval == Gtk.keysyms.Down:
            self.select_next()

    def complete(self):
        self.complete_callback(self.completions[self.get_selected()]['completion'])

    def focus_out_event(self, *args):
        self.hide()
    
    def get_selected(self):
        """Get the selected row."""

        selection = self.view.get_selection()
        return selection.get_selected_rows()[1][0][0]

    def init_frame(self):
        """Initialize the frame and scroller around the tree view."""

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scroller.add(self.view)
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        hbox = Gtk.HBox()
        hbox.add(scroller)

        scroller_text = Gtk.ScrolledWindow() 
        scroller_text.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller_text.add(self.text)
        hbox.add(scroller_text)
        frame.add(hbox)
        self.add(frame)

    def init_tree_view(self):
        """Initialize the tree view listing the completions."""

        self.store = Gtk.ListStore(GObject.TYPE_STRING)
        self.view = Gtk.TreeView(self.store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=0)
        self.view.append_column(column)
        self.view.set_enable_search(False)
        self.view.set_headers_visible(False)
        self.view.set_rules_hint(True)
        selection = self.view.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        self.view.set_size_request(200, 200)
        self.view.connect('row-activated', self.row_activated)

    def row_activated(self, tree, path, view_column, data = None):
        self.complete()

    def select_next(self):
        """Select the next completion."""

        row = min(self.get_selected() + 1, len(self.store) - 1)
        selection = self.view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self.view.scroll_to_cell(row)
        self.text_buffer.set_text(self.completions[self.get_selected()]['info'])

    def select_previous(self):
        """Select the previous completion."""

        row = max(self.get_selected() - 1, 0)
        selection = self.view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self.view.scroll_to_cell(row)
        self.text_buffer.set_text(self.completions[self.get_selected()]['info'])

    def set_completions(self, completions):
        """Set the completions to display."""

        self.completions = completions
        self.completions.reverse()
        self.resize(1, 1)
        self.store.clear()
        for completion in completions:
            self.store.append([unicode(completion['abbr'])])
        self.view.columns_autosize()
        self.view.get_selection().select_path(0)
        self.text_buffer.set_text(self.completions[self.get_selected()]['info'])

    def set_font_description(self, font_desc):
        """Set the label's font description."""

        self.view.modify_font(font_desc)


class CompletionPlugin(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):

    """Complete python code with the tab key."""

    __gtype_name__ = "CompletionPlugin"
    window = GObject.property(type=Gedit.Window)
    
    re_alpha = re.compile(r"\w+", re.UNICODE | re.MULTILINE)
    re_non_alpha = re.compile(r"\W+", re.UNICODE | re.MULTILINE)

    def __init__(self):
        print("Constructing plugin")
        
        GObject.Object.__init__(self)
        
        self.completes = None
        self.completions = None
        self.popup = None
        self.name = "CompletionPlugin"

    def do_activate(self):
        """Activate plugin."""
        print("Activating plugin")
        
        self.popup = CompletionWindow(self.window, self.complete)
        handler_ids = []
        callback = self.on_tab_added
        handler_id = self.window.connect("tab-added", callback)
        handler_ids.append(handler_id)
        self.window.set_data(self.name, handler_ids)
        for view in self.window.get_views():
            self.connect_view(view)
        print("Activation complete")

    def cancel(self):
        """Hide the completion window and return False."""

        self.hide_popup()
        return False

    def complete(self, completion):
        """Complete the current word."""

        doc = self.window.get_active_document()
        index = self.popup.get_selected()
        doc.insert_at_cursor(completion)
        self.hide_popup()
        
    def connect_view(self, view):
        """Connect to view's signals."""

        handler_ids = []
        callback = self.on_view_key_press_event
        handler_id = view.connect("key-press-event", callback)
        handler_ids.append(handler_id)
        view.set_data(self.name, handler_ids)

    def do_create_configure_widget(self):
        """Creates and displays a ConfigurationDialog."""
        dlg = configurationdialog.ConfigurationDialog()
        return dlg

    def do_deactivate(self):
        """Deactivate plugin."""

        widgets = [self.window]
        widgets.append(self.window.get_views())
        widgets.append(self.window.get_documents())
        for widget in widgets:
            handler_ids = widget.get_data(self.name)
            for handler_id in handler_ids:
                widget.disconnect(handler_id)
            widget.set_data(self.name, None)
        self.hide_popup()
        self.popup = None

    def display_completions(self, view, event):
        """Find completions and display them."""

        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        start = insert.copy()
        while start.backward_char():
            char = unicode(start.get_char())
            if not self.re_alpha.match(char) and not char == ".":
                start.forward_char()
                break
        incomplete = unicode(doc.get_text(start, insert, True))
        incomplete += unicode(event.string)
        if incomplete.isdigit():
            return self.cancel()
        completes =  complete( doc.get_text(*doc.get_bounds()), incomplete, insert.get_line())
        if not completes:
            return self.cancel()
        self.completes = completes

        if "." in incomplete:
            incompletelist = incomplete.split('.')
            newword = incompletelist[-1]
            self.completions = list(x['abbr'][len(newword):] for x in completes)
            length = len(newword)
        else:
            self.completions = list(x['abbr'][len(incomplete):] for x in completes)
            length = len(incomplete)
        for x in completes:
            x['completion'] = x['abbr'][length:]
        window = Gtk.TextWindowType.TEXT
        rect = view.get_iter_location(insert)
        x, y = view.buffer_to_window_coords(window, rect.x, rect.y)
        x, y = view.translate_coordinates(self.window, x, y)
        self.show_popup(completes, x, y)

    def hide_popup(self):
        """Hide the completion window."""

        self.popup.hide()
        self.completes = None
        self.completions = None

    def is_configurable(self):
        """Show the plugin as configurable in gedits plugin list."""
        return True

    def on_view_key_press_event(self, view, event):
        """Display the completion window or complete the current word."""
        active_doc = self.window.get_active_document()
        if active_doc is None or active_doc.get_mime_type() != 'text/x-python':
            return self.cancel()

        # FIXME This might result in a clash with other plugins eg. snippets
        # FIXME This code is not portable! 
        #  The "Alt"-key might be mapped to something else
        # TODO Find out which keybinding are already in use.
        keybinding = configuration.getKeybindingCompleteTuple()
        ctrl_pressed = (event.state & Gdk.ModifierType.CONTROL_MASK) == Gdk.ModifierType.CONTROL_MASK
        alt_pressed = (event.state & Gdk.ModifierType.MOD1_MASK) == Gdk.ModifierType.MOD1_MASK
        shift_pressed = (event.state & Gdk.ModifierType.SHIFT_MASK) == Gdk.ModifierType.SHIFT_MASK
        keyval = Gdk.keyval_from_name(keybinding[configuration.KEY])
        key_pressed = (event.keyval == keyval)

        # It's ok if a key is pressed and it's needed or
        # if a key is not pressed if it isn't needed.
        ctrl_ok = not (keybinding[configuration.MODIFIER_CTRL] ^ ctrl_pressed )
        alt_ok =  not (keybinding[configuration.MODIFIER_ALT] ^ alt_pressed )
        shift_ok = not (keybinding[configuration.MODIFIER_SHIFT] ^ shift_pressed )

        if ctrl_ok and alt_ok and shift_ok and key_pressed or event.keyval == Gdk.KEY_period:
            return self.display_completions(view, event)
        
        return self.cancel()

    def on_tab_added(self, window, tab, data=None):
        """Connect the document and view in tab."""

        context = tab.get_view().get_pango_context()
        font_desc = context.get_font_description()
        self.popup.set_font_description(font_desc)
        self.connect_view(tab.get_view())


    def show_popup(self, completions, x, y):
        """Show the completion window."""

        root_x, root_y = self.window.get_position()
        self.popup.move(root_x + x + 24, root_y + y + 44)
        self.popup.set_completions(completions)
        self.popup.show_all()
        

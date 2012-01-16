"""
A widget for entering keybindings, e.g. ctr+alt+space.

Signals: keybinding-changed
"""
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

from gi.repository import Gtk, Gdk, GObject
import string

import logging

ACTIVATED_TEXT = "Press new keybinding..."
LOG_NAME = "KeybindingWidget"
COLOR_FOCUS_IN = "white"
DEFAULT_TEXT = "None set"
WIDTH_CHARS = 18

log = logging.getLogger(LOG_NAME)

class KeybindingWidget(Gtk.EventBox):
    def __init__(self):
        Gtk.EventBox.__init__(self)
        log.info("Initializing KeybindingWidget.")
        
        self._label = Gtk.Label()
        self._label.set_text(DEFAULT_TEXT)
        self._label.set_width_chars(WIDTH_CHARS)
        self._label.set_alignment(0.0, 0.5)
        self._label.set_can_focus(False)
        self.add(self._label)
        
        events = Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.FOCUS_CHANGE_MASK
        self.add_events(events)
        
        self.active = False
        
        self._keybinding = []
    
    def getKeybinding(self):
        return self._keybinding
    
    def setKeybinding(self, keybinding):
        self._keybinding = keybinding
        self._label.set_text(keybinding)
        
    def do_button_press_event(self, event):
        log.info("do_button_press_event()")
        log.info("Grabbing focus.")
        self.set_can_focus(True)
        self.grab_focus()
        self.modify_bg(Gtk.STATE_NORMAL, gdk.color_parse(COLOR_FOCUS_IN))
        self.active = True

    def do_key_press_event(self, event):
        if not self.active:
            return False
        log.info("do_key_press_event()")
        key_name = gdk.keyval_name(event.keyval)
        log.info("key_name = " + str(key_name))
        
        # Deactivate on Escape
        if key_name == "Escape":
            self.deactivate()
            return True

        keybinding = []
        
        # FIXME Doesn't work with any super combination
        # FIXME What if keys are already used by another plugin?
        if key_name == "space" or key_name == "Tab" \
            or key_name in string.ascii_letters:
            # Check for Ctrl
            if event.state & Gdk.CONTROL_MASK:
                log.info("Ctrl held down.")
                keybinding.append("ctrl")
            # Check for Alt
            if event.state & Gdk.MOD1_MASK:
                log.info("Alt held down.")
                keybinding.append("alt")
            # Check for Shift
            if event.state & Gdk.SHIFT_MASK:
                log.info("Shift held down.")
                keybinding.append("shift")

            keybinding.append(key_name.lower())
            log.info("Setting key keybinding to " + '+'.join(keybinding))
            self.setKeybinding('+'.join(keybinding))
            self.deactivate()
            self.emit("keybinding-changed", self.getKeybinding())
            return True
            
    def do_focus_out_event(self, event):
        log.info("do_focus_out_event()")
        self.deactivate()
        
    def deactivate(self):
        # Revert color back to normal
        default_bg_color = self.parent.get_style().bg[Gtk.STATE_NORMAL]
        self.modify_bg(Gtk.STATE_NORMAL, default_bg_color)
        self.set_can_focus(False)
        self.active = False
        keybinding = self.getKeybinding()
        
        if not keybinding:
            self._label.set_text(DEFAULT_TEXT)
        else:
            self._label.set_text(keybinding)
        

GObject.type_register(KeybindingWidget)
GObject.signal_new("keybinding-changed", KeybindingWidget,
                       GObject.SIGNAL_RUN_LAST,
                       GObject.TYPE_NONE,
                       (GObject.TYPE_PYOBJECT,))

# Tests below

def on_keybinding_changed(widget, keybinding):
    print "on_keybinding_changed()"
    print "New keybinding is", keybinding

if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(logging.DEBUG)

    win = Gtk.Window()
    win.set_border_width(5)
    win.set_title('KeybindingWidget test')
    win.connect('delete-event', Gtk.main_quit)

    hbox = Gtk.HBox(homogeneous=False, spacing=4)
    win.add(hbox)

    table = Gtk.Table(2, 2, homogeneous=False)
    table.set_row_spacings(4)
    table.set_col_spacings(4)
    hbox.pack_start(table, False, False, 0)

    lblKeybinding = Gtk.Label()
    lblKeybinding.set_text("Keybinding:")
    # Put in upper left quadrant
    table.attach(lblKeybinding, 0, 1, 0, 1, xoptions=False, yoptions=False)
    
    kbind = KeybindingWidget()
    # Put in upper right quadrant
    table.attach(kbind, 1, 2, 0, 1, xoptions=False, yoptions=False)
    kbind.connect("keybinding-changed", on_keybinding_changed)

    lblStuff = Gtk.Label()
    lblStuff.set_text("Enter stuff:")
    # Put in lower left quadrant
    table.attach(lblStuff, 0, 1, 1, 2, xoptions=False, yoptions=False)
    
    entryStuff = Gtk.Entry()
    # Put in lower right quadrant
    table.attach(entryStuff, 1, 2, 1, 2, xoptions=False, yoptions=False)
    
    win.show_all()

    Gtk.main()

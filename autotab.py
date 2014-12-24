# -*- coding: utf-8 -*-
#
# Auto Tab for gedit, automatically detect tab preferences for source files.
# Can be used together with the Modelines plugin without ill effect, modelines
# will take precedence.
#
# Copyright (C) 2007-2010 Kristoffer Lundén (kristoffer.lunden@gmail.com)
# Copyright (C) 2007 Lars Uebernickel (larsuebernickel@gmx.de)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject, Gio, Gedit
from gi.repository import Gtk, Gdk
import operator

# Main class
class AutoTab(GObject.Object, Gedit.WindowActivatable):
  __gtype_name__ = "AutoTab"

  window = GObject.property(type=Gedit.Window)

  def do_activate(self):
    self.spaces_instead_of_tabs = False
    self.tabs_width = 2

    # Prime the statusbar
    self.statusbar = self.window.get_statusbar()
    self.context_id = self.statusbar.get_context_id("AutoTab")
    self.message_id = None

    settings = Gio.Settings("org.gnome.gedit.preferences.editor")

    self.new_tabs_size(settings)
    self.new_insert_spaces(settings)

    settings.connect("changed::tabs-size", self.new_tabs_size)
    settings.connect("changed::insert-spaces", self.new_insert_spaces)

    for view in self.window.get_views():
      self.connect_handlers(view)
      self.auto_tab(view.get_buffer(), None, view)

    tab_added_id = self.window.connect("tab_added", lambda w, t: self.connect_handlers(t.get_view()))
    self.window.AutoTabPluginHandlerId = tab_added_id

  def do_deactivate(self):
    tab_added_id = self.window.AutoTabPluginHandlerId
    self.window.disconnect(tab_added_id)
    self.window.AutoTabPluginHandlerId = None

    for view in self.window.get_views():
      self.disconnect_handlers(view)

    if self.message_id:
      if hasattr(self.statusbar, 'remove_message'):
        self.statusbar.remove_message(self.context_id, self.message_id)
      else:
        self.statusbar.remove(self.context_id, self.message_id)


  def connect_handlers(self, view):
    doc = view.get_buffer()
    # Using connect_after() because we want other plugins to do their
    # thing first.
    loaded_id = doc.connect_after("loaded", self.auto_tab, view)
    saved_id  = doc.connect_after("saved", self.auto_tab, view)
    pasted_id = view.connect("paste-clipboard", self.on_paste)
    #doc.AutoTabPluginHandlerIds = (loaded_id, saved_id, pasted_id)
    doc.AutoTabPluginHandlerIds = (loaded_id, saved_id)

  def disconnect_handlers(self, view):
    doc = view.get_buffer()
    #loaded_id, saved_id, pasted_id = doc.AutoTabPluginHandlerIds
    loaded_id, saved_id = doc.AutoTabPluginHandlerIds
    doc.disconnect(loaded_id)
    doc.disconnect(saved_id)
    #view.disconnect(pasted_id)
    doc.AutoTabPluginHandlerIds = None

  def on_clipboard_text(self, clipboard, text, view):
    doc = view.get_buffer()

    if text is None:
      # nothing on clipboard
      return

    # start and end of selection, or the same if no selection
    start_iter = doc.get_iter_at_mark(doc.get_insert())
    end_iter = doc.get_iter_at_mark(doc.get_selection_bound())

    # the line above and below selection/cursor position
    start_line = start_iter.get_line()
    end_line = end_iter.get_line()
    if start_line > 0:
      start_line -= 1
    if end_line < doc.get_line_count() - 1:
      end_line += 1
    line_iter = doc.get_iter_at_line(start_iter.get_line())


    before_iter = doc.get_iter_at_line(start_line)
    after_iter = doc.get_iter_at_line(end_line)

    space = view.get_insert_spaces_instead_of_tabs()
    size = view.get_tab_width()
    if space:
      tab = " "
    else:
      tab = "\t"
      size = 1

    # check the position we are pasting on, to see if we are inside non-whitespace
    # if so, assume position is already correct and do not paste
    # get this before doing forward_char
    text_before_paste = doc.get_text(line_iter, start_iter, True)

    while line_iter.get_char() == tab:
      line_iter.forward_char()
    while before_iter.get_char() == tab:
      before_iter.forward_char()

    # pick the line, before or after with the most indent:
    #indent = max(line_iter.get_line_offset(), before_iter.get_line_offset(), after_iter.get_line_offset())
    indent = max(line_iter.get_line_offset(), before_iter.get_line_offset())

    inside_line = len(text_before_paste.translate(" \t")) > 0
    if not inside_line:
      doc.delete(line_iter, start_iter)
    doc.delete_selection(False, True)

    # this rounds to multiple of the tab settings, if needed
    # ie if indent is 7 and the tab size is 2, it will go to 6 instead
    if (space):
      indent /= size

    lines = text.splitlines(True)

    doc.begin_user_action()

    last_line_indent = -1
    for line in lines:
      for line_indent in range(0, len(line)):
        if line[line_indent] != tab:
          break

      if last_line_indent != -1: # not first line
        if line_indent > last_line_indent:
          indent += 1
        elif line_indent < last_line_indent:
          indent -= 1

      prefix = tab * round(indent * size)

      if inside_line and last_line_indent == -1: # first line
        doc.insert_at_cursor(line)
      else:
        doc.insert_at_cursor(prefix + line.lstrip())
      last_line_indent = line_indent

    doc.end_user_action()
    view.scroll_mark_onscreen(doc.get_insert())
    view.scroll_mark_onscreen(doc.get_insert())




  # capture paste
  def on_paste(self, view):
    clipboard = Gtk.Clipboard.get_for_display(view.get_display(), Gdk.SELECTION_CLIPBOARD)
    clipboard.request_text(self.on_clipboard_text, view)
    view.stop_emission('paste-clipboard')

  # If default tab size changes
  def new_tabs_size(self, settings, key=None):
    self.tabs_width = settings.get_value("tabs-size").get_uint32()
    self.update_tabs(self.tabs_width, self.spaces_instead_of_tabs)

  # If default space/tabs changes
  def new_insert_spaces(self, settings, key=None):
    self.spaces_instead_of_tabs = settings.get_boolean("insert-spaces")
    self.update_tabs(self.tabs_width, self.spaces_instead_of_tabs)

  # Update the values and set a new statusbar message
  def update_tabs(self, size, space):
    view = self.window.get_active_view()
    if view:
      view.set_tab_width(size)
      view.set_insert_spaces_instead_of_tabs(space)
      self.update_status()

  # Statusbar message
  def update_status(self):
    view = self.window.get_active_view()
    if view:
      space = view.get_insert_spaces_instead_of_tabs()
      size = view.get_tab_width()
      if space:
        message = "%i Spaces" % size
      else:
        message = "Tabs"
      if self.message_id:
        if hasattr(self.statusbar, 'remove_message'):
          self.statusbar.remove_message(self.context_id, self.message_id)
        else:
          self.statusbar.remove(self.context_id, self.message_id)

      self.message_id = self.statusbar.push(self.context_id, "Indentation: %s" % message)

  # Make sure correct tabs are displayed
  def do_update_state(self):
    self.update_status()

  # Main workhorse, identify what tabs we should use and use them.
  def auto_tab(self, doc, *args):
    # gedit < 3.14 passes an error paramater as the first argument,
    # gedit >= 3.14 does not.
    if len(args) > 1:
      error = args[0]
      view = args[1]
    else:
      error = None
      view = args[0]

    if error is not None:
      pass

    # Other plugins compatibility, other plugins can do
    # view.AutoTabSkip = True
    # and Auto Tab will skip that document as long as this value is true.
    if hasattr(view, 'AutoTabSkip') and view.AutoTabSkip:
      self.update_status()
      return

    # Modelines plugin compatibility, if ModelineOptions has been set with
    # any tab related data, we assume Modelines has done the right thing and
    # just update our UI with the existing settings.
    if hasattr(view, 'ModelineOptions') and view.ModelineOptions:
      modeline = view.ModelineOptions
      if modeline.has_key("tabs-width") or modeline.has_key("use-tabs"):
        self.update_status()
        return

    # End of Modelines stuff,
    # start of Auto Tabs own stuff

    # Special case for makefiles, so the plugin uses tabs even for the empty file:
    if doc.get_mime_type() == "text/x-makefile" or doc.get_short_name_for_display() == "Makefile":
      self.update_tabs(self.tabs_width, False)
      return

    start, end = doc.get_bounds()

    if not end:
      return
    text = doc.get_text(start, end, True)

    indent_count = {'tabs':0, 2:0, 3:0, 4:0, 8:0}
    seen_tabs = 0
    seen_spaces = 0
    last_indent = 0

    for line in text.splitlines():
      if len(line) == 0:
        continue

      if not line[0].isspace():
        last_indent = 0
        continue

      if line[0] == '\t':
        indent_count['tabs'] += 1
        seen_tabs += 1
        continue
      elif line[0] == ' ':
        seen_spaces += 1

      indent = 0
      for indent in range(0, len(line)):
        if line[indent] != ' ':
          break

      for spaces in indent_count.keys():
        if type(spaces) is not int:
          continue

        if (indent % spaces) == 0:
          indent_count[spaces] += 1

        # double weight if this represents +1 indent
        if (indent - last_indent == spaces):
          indent_count[spaces] += 1

      last_indent = indent

    # no indentations detected
    if sum(indent_count.values()) == 0:
      # if we've seen tabs or spaces, default to those
      # can't guess at size, so using default
      if seen_tabs or seen_spaces:
        if seen_tabs > seen_spaces:
          self.update_tabs(self.tabs_width, False)
        else:
          self.update_tabs(self.tabs_width, True)
      return

    winner = None

    keys = indent_count.keys()
    for key in keys:
      if (winner is None) or (indent_count[key] > indent_count[winner]):
        winner = key

    if winner == 'tabs':
      self.update_tabs(self.tabs_width, False)
    else:
      self.update_tabs(winner, True)

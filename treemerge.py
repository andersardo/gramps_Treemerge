#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
"""Match persons RGD style."""

import sys
import os

#-------------------------------------------------------------------------
#
# GNOME libraries
#
#-------------------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import GooCanvas

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import URL_MANUAL_PAGE
from gramps.gen import datehandler
from gramps.gen.utils.db import (get_birth_or_fallback, get_death_or_fallback)
from gramps.gen.lib import Event, Person
from gramps.gui.utils import ProgressMeter
from gramps.gui.plug import tool
from gramps.gen.soundex import soundex, compare
from gramps.gen.display.name import displayer as name_displayer
from gramps.gui.dialog import OkDialog
from gramps.gui.listmodel import ListModel
from gramps.gen.errors import WindowActiveError
from gramps.gui.merge import MergePerson
from gramps.gui.display import display_help
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.dialog import RunDatabaseRepair
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from gramps.gui.glade import Glade

#-------------------------------------------------------------------------
#
# Fulltextdatabase Whoosh
#
#-------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from match import Match
from matchview import ViewPersonMatch

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------
_val2label = {
    0.5 : _("Low"),
    0.75  : _("Medium"),
    0.9  : _("High"),
    }

WIKI_HELP_PAGE = '%s_-_Tools' % URL_MANUAL_PAGE
WIKI_HELP_SEC = _('Find_Possible_Duplicate_People', 'manual')

#-------------------------------------------------------------------------
#
#
#
#-------------------------------------------------------------------------
def is_initial(name):
    if len(name) > 2:
        return 0
    elif len(name) == 2:
        if name[0] == name[0].upper() and name[1] == '.':
            return 1
    else:
        return name[0] == name[0].upper()

#-------------------------------------------------------------------------
#
# The Actual tool.
#
#-------------------------------------------------------------------------
class TreeMerge(tool.Tool, ManagedWindow):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate

        tool.Tool.__init__(self, dbstate, options_class, name)
        self.uistate = uistate
        self.track = []
        ManagedWindow.__init__(self, self.uistate, self.track, self.__class__)
        self.dbstate = dbstate
        self.map = {}
        self.list = []
        self.index = 0
        self.merger = None
        self.mergee = None
        self.removed = {}
        self.update = callback
        self.use_soundex = 1
        self.dellist = set()
        self.length = len(self.list)

        top = Glade(toplevel="treemerge", also_load=["liststore1"])

        # retrieve options
        threshold = self.options.handler.options_dict['threshold']
        use_soundex = self.options.handler.options_dict['soundex']

        my_menu = Gtk.ListStore(str, object)
        for val in sorted(_val2label, reverse=True):
            my_menu.append([_val2label[val], val])

        self.soundex_obj = top.get_object("soundex1")
        self.soundex_obj.set_active(self.use_soundex)
        self.soundex_obj.show()

        self.menu = top.get_object("menu1")
        self.menu.set_model(my_menu)
        self.menu.set_active(0)

        mlist = top.get_object("mlist1")
        mtitles = [
            (_('Rating'),3,75),
            (_('First Person'),1,200),
            (_('Second Person'),2,200),
            ('',-1,0)
        ]
        self.mlist = ListModel(mlist, mtitles, event_func=self.do_merge)

        self.infolbl = top.get_object("title3")
        window = top.toplevel
        self.set_window(window, top.get_object('title'),
                        _('Find/Merge Probably Identical Persons'))
        self.setup_configs('interface.duplicatepeopletool', 350, 220) #???
        """
        top.connect_signals({
            "on_do_merge_clicked"   : self.__dummy,
            "on_help_show_clicked"  : self.__dummy,
            "on_delete_show_event"  : self.__dummy,
            "on_merge_ok_clicked"   : self.on_merge_ok_clicked,
            "destroy_passed_object" : self.close,
            "on_help_clicked"       : self.on_help_clicked,
            "on_delete_merge_event" : self.close,
            "on_delete_event"       : self.close,
            })

        """
        infobtn = top.get_object("infobtn")
        infobtn.connect('clicked', self.info)
        matchbtn = top.get_object("matchbtn")
        matchbtn.connect('clicked', self.do_match)
        compbtn = top.get_object("cmpbtn")
        compbtn.connect('clicked', self.do_comp)
        mergebtn = top.get_object("mergebtn")
        mergebtn.connect('clicked', self.do_merge)
        closebtn = top.get_object("closebtn")
        closebtn.connect('clicked', self.close)
        self.show()

    def notImplem(self, txt):
        self.infolbl.set_label("Control: %s - Not implemented yet" % txt)

    def infoMsg(self, txt):
        self.infolbl.set_label("Control: %s" % txt)

    def info(self, *obj):
        self.notImplem("Infobutton pressed")
        
    #def do_merge(self, *obj):
    #    print('call merge_person plugin')

    #def build_menu_names(self, obj):
    #    return (_("Tool settings"),_("Find Duplicates tool"))

    def on_help_clicked(self, obj):
        """Display the relevant portion of Gramps manual"""
        self.notImplem("Help")
        #display_help(WIKI_HELP_PAGE , WIKI_HELP_SEC)

    def do_match(self, obj):
        threshold = self.menu.get_model()[self.menu.get_active()][1]
        self.use_soundex = int(self.soundex_obj.get_active())
        self.progress = ProgressMeter(_('Find matches for persons'),
                                      _('Looking for duplicate/matching people'),
                                      parent=self.window)

        matcher = Match(self.dbstate.db, self.progress, self.use_soundex, threshold)
        try:
            matcher.do_find_matches()
            self.map = matcher.map
            self.list = matcher.list
        except AttributeError as msg:
            RunDatabaseRepair(str(msg), parent=self.window)
            return

        self.options.handler.options_dict['threshold'] = threshold
        self.options.handler.options_dict['soundex'] = self.use_soundex
        # Save options
        self.options.handler.save_options()
        self.length = len(self.list)

        if len(self.map) == 0:
            OkDialog(
                _("No matches found"),
                _("No potential duplicate people were found"),
                parent=self.window)
        else:
            self.redraw()
            self.show() #??
        """
            try:
                DuplicatePeopleToolMatches(self.dbstate, self.uistate,
                                           self.track, self.list, self.map,
                                           self.update)
            except WindowActiveError:
                pass
        """

    def redraw(self):
        list = []
        for p1key, p1data in self.map.items():
            if p1key in self.dellist:
                continue
            (p2key, c) = p1data
            if p2key in self.dellist:
                continue
            if p1key == p2key:
                continue
            list.append((c, p1key, p2key))

        self.mlist.clear()
        for (c, p1key, p2key) in list:
            c1 = "%5.2f" % c
            c2 = "%5.2f" % (100-c)
            p1 = self.db.get_person_from_handle(p1key)
            p2 = self.db.get_person_from_handle(p2key)
            if not p1 or not p2:
                continue
            pn1 = "%s %s" % (p1.gramps_id, name_displayer.display(p1))
            pn2 = "%s %s" % (p2.gramps_id, name_displayer.display(p2))  #name_displayer.display(p2)
            self.mlist.add([c1, pn1, pn2, c2],(p1key, p2key))

    #    def on_do_merge_clicked(self, obj):
    def do_merge(self, obj):
        store, iter = self.mlist.selection.get_selected()
        if not iter:
            self.infoMsg("Please select a match above")
            return
        (self.p1, self.p2) = self.mlist.get_object(iter)
        self.notImplem("Merge 2 matched persons")
        #print('List', self.p1, self.p2)
        MergePerson(self.dbstate, self.uistate, self.track, self.p1, self.p2,
                    self.on_update, True)

    def do_comp(self, obj):
        #print('Compare 2 persons, tree-view')
        store, iter = self.mlist.selection.get_selected()
        if not iter:
            self.infoMsg("Please select a match above")
            return
        (self.p1, self.p2) = self.mlist.get_object(iter)
        GraphComparePerson(self.dbstate, self.uistate, self.track, self.p1, self.p2, self.on_update) #FIX

    def on_update(self):  #??? FIX behövs?
        if self.db.has_person_handle(self.p1):
            titanic = self.p2
        else:
            titanic = self.p1
        self.dellist.add(titanic)
        #??self.update()
        self.redraw()

    #def update_and_destroy(self, obj):
    def close(self, obj, t=None):
        self.list = None
        #self.update(1)
        #self.graphview.close()
        ManagedWindow.close(self, *obj)

    def person_delete(self, handle_list):
        """ deal with person deletes outside of the tool """
        self.dellist.update(handle_list)
        self.redraw()

    def __dummy(self, obj):
        """dummy callback, needed because a shared glade file is used for
        both toplevel windows and all signals must be handled.
        """
        pass

class GraphComparePerson(ManagedWindow):

    def __init__(self, dbstate, uistate, track, p1, p2, callback):
        self.uistate = uistate
        self.track = track
        ManagedWindow.__init__(self, self.uistate, self.track, self.__class__)
        self.update = callback
        self.db = dbstate.db
        self.dbstate = dbstate
        self.p1 = p1
        self.p2 = p2
        #print('GraphComparePerson got', self.p1, self.p2)

        top = Glade(toplevel="compgraph")
        window = top.toplevel
        self.set_window(window, top.get_object('title'), 'Graph Compare Potential Merges')
        self.setup_configs('interface.duplicatepeopletoolmatches', 800, 400) #?
        scrolled_win = top.get_object('scrwin')
        self.canvas = GooCanvas.Canvas()
        #self.canvas.connect("scroll-event", self.scroll_mouse)
        self.canvas.props.units = Gtk.Unit.POINTS
        self.canvas.props.resolution_x = 72
        self.canvas.props.resolution_y = 72
        scrolled_win.add(self.canvas)

        self.graphView = ViewPersonMatch(self.dbstate, self.uistate, self.canvas, track, self.p1, self.p2, callback)

        self.closebtn = top.get_object("grclose")
        self.closebtn.connect('clicked', self.close)
        self.okbtn = top.get_object("grok")
        self.okbtn.connect('clicked', self.ok)
        self.okbtn.set_label("Merge")
        self.infobtn = top.get_object("grinfo")
        self.infobtn.connect('clicked', self.info)
        self.infobtn.set_label("Info - Not implemented")
        """
        top.connect_signals({
            "destroy_passed_object" : self.close,
            "on_do_merge_clicked"   : self.on_do_merge_clicked,
            "on_help_show_clicked"  : self.on_help_clicked,
            "on_delete_show_event"  : self.close,
            "on_merge_ok_clicked"   : self.__dummy,
            "on_help_clicked"       : self.__dummy,
            "on_delete_merge_event" : self.__dummy,
            "on_delete_event"       : self.__dummy,
            })
        """
        self.db.connect("person-delete", self.person_delete)
        #??MergePerson(self.dbstate, self.uistate, self.track, self.p1, self.p2,
        #??            self.on_update, True)

        self.redraw()
        self.show()

    def close(self, obj, t=None):
        #self.graphView.close()
        ManagedWindow.close(self, *obj)

    def on_help_clicked(self, obj):
        """Display the relevant portion of Gramps manual"""
        display_help(WIKI_HELP_PAGE , WIKI_HELP_SEC)

    def ok(self, obj):
        MergePerson(self.dbstate, self.uistate, self.track, self.p1, self.p2,
                    self.on_update, True)

    def info(self, *obj):
        print('grinfo button clicked')

    def redraw(self):
        pass # ??

    def on_do_merge_clicked(self, obj):
        pass

    def on_update(self):
        self.close('')
        #self.update()
        #self.redraw()

    def update_and_destroy(self, obj):
        self.update(1)
        self.close()

    def person_delete(self, handle_list):
        """ deal with person deletes outside of the tool """
        #self.dellist.update(handle_list)
        self.redraw()

    def __dummy(self, obj):
        """dummy callback, needed because a shared glade file is used for
        both toplevel windows and all signals must be handled.
        """
        pass

#------------------------------------------------------------------------
#
#
#
#------------------------------------------------------------------------
class TreeMergeOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name,person_id=None):
        tool.ToolOptions.__init__(self, name,person_id)

        # Options specific for this report
        self.options_dict = {
            'soundex'   : 1,
            'threshold' : 0.75,
        }
        self.options_help = {
            'soundex'   : ("=0/1","Whether to use SoundEx codes",
                           ["Do not use SoundEx","Use SoundEx"],
                           True),
            'threshold' : ("=num","Threshold for tolerance",
                           "Floating point number")
            }

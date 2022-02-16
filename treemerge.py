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
from gramps.gen.merge import MergePersonQuery
from gramps.gui.dialog import QuestionDialog2

#from libaccess import *

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

_automergecutoff = {
    0.99: "0.99",
    0.95: "0.95",
    0.90: "0.90"
    }
#WIKI_HELP_PAGE = '%s_-_Tools' % URL_MANUAL_PAGE
#WIKI_HELP_SEC = _('Find_Possible_Duplicate_People', 'manual')

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
class TreeMerge(tool.Tool, ManagedWindow):  #CHECK use BatchTool when using automated merge

    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate

        tool.Tool.__init__(self, dbstate, options_class, name)
        self.uistate = uistate
        self.track = []
        ManagedWindow.__init__(self, self.uistate, self.track, self.__class__)
        self.dbstate = dbstate
        #init(self.dbstate.db)  # for libaccess
        self.map = {}
        self.list = []
        self.index = 0
        self.merger = None
        self.mergee = None
        self.removed = {}
        self.dellist = set()
        self.length = len(self.list)
        self.p1 = None
        self.p2 = None

        top = Glade(toplevel="treemerge", also_load=["liststore1", "liststore2", "liststore3"])

        # retrieve options
        threshold = self.options.handler.options_dict['threshold']
        use_soundex = self.options.handler.options_dict['soundex']
        algoritm = self.options.handler.options_dict['algoritm']
        
        my_menu = Gtk.ListStore(str, object)
        for val in sorted(_val2label, reverse=True):
            my_menu.append([_val2label[val], val])

        #my_algmenu = Gtk.ListStore(str, object)
        #for val in sorted(_alg2label, reverse=True):
        #    my_algmenu.append([_alg2label[val], val])

        my_automergecutoff = Gtk.ListStore(str, object)
        for val in sorted(_automergecutoff, reverse=True):
            my_automergecutoff.append([_automergecutoff[val], val])

        self.soundex_obj = top.get_object("soundex1")
        self.soundex_obj.set_active(0) # Default value
        self.soundex_obj.show()

        self.menu = top.get_object("menu1")
        self.menu.set_model(my_menu)
        self.menu.set_active(0)

        algoritm = Gtk.ListStore(str, object)
        algoritm. append(["SVM", "svm"])
        algoritm. append(["Score", "score"])
        self.algmenu = top.get_object("algoritm")
        self.algmenu.set_model(algoritm)
        self.algmenu.set_active(0)

        self.automergecutoff = top.get_object("automergecutoff")
        self.automergecutoff.set_model(my_automergecutoff)
        self.automergecutoff.set_active(1)

        mlist = top.get_object("mlist1")
        mtitles = [
            (_('Rating'), 3, 75),
            (_('First Person'), 1, 300),
            (_('Second Person'), 2, 300),
            ('',-1,0)
        ]
        self.mlist = ListModel(mlist, mtitles, event_func=self.do_merge)

        self.infolbl = top.get_object("title3")
        window = top.toplevel
        self.set_window(window, top.get_object('title'),
                        _('Find/Merge Probably Identical Persons'))
        self.setup_configs('interface.duplicatepeopletool', 350, 220)
        infobtn = top.get_object("infobtn")
        infobtn.connect('clicked', self.info)
        matchbtn = top.get_object("matchbtn")
        matchbtn.connect('clicked', self.do_match)
        compbtn = top.get_object("cmpbtn")
        compbtn.connect('clicked', self.do_comp)
        mergebtn = top.get_object("mergebtn")
        mergebtn.connect('clicked', self.do_merge)
        automergebtn = top.get_object("automerge")
        automergebtn.connect('clicked', self.do_automerge)
        automergebtn.set_tooltip_text('WARN automerge')
        closebtn = top.get_object("closebtn")
        closebtn.connect('clicked', self.close)

        self.dbstate.connect('database-changed', self.redraw) #??
        self.db.connect("person-delete", self.person_delete)  #??

        self.show()

    def notImplem(self, txt):
        self.infolbl.set_label("Control: %s - Not implemented yet" % txt)

    def infoMsg(self, txt):
        self.infolbl.set_label("Control: %s" % txt)

    def info(self, *obj):
        self.notImplem("Infobutton pressed")
        
    def on_help_clicked(self, obj):
        """Display the relevant portion of Gramps manual"""
        self.notImplem("Help")
        #display_help(WIKI_HELP_PAGE , WIKI_HELP_SEC)

    def do_match(self, obj):
        threshold = self.menu.get_model()[self.menu.get_active()][1]
        use_soundex = int(self.soundex_obj.get_active())
        algoritm = self.algmenu.get_model()[self.algmenu.get_active()][1]
        self.progress = ProgressMeter(_('Find matches for persons'),
                                      _('Looking for duplicate/matching people'),
                                      parent=self.window)

        matcher = Match(self.dbstate.db, self.progress, use_soundex, threshold, algoritm)
        try:
            matcher.do_find_matches()
            self.map = matcher.map
            self.list = matcher.list
        except AttributeError as msg:
            RunDatabaseRepair(str(msg), parent=self.window)
            return

        self.options.handler.options_dict['threshold'] = threshold
        self.options.handler.options_dict['soundex'] = use_soundex
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

    def redraw(self):
        list = []
        for p1key, p1data in sorted(self.map.items(), key=lambda item: item[1][1], reverse=True):
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
            #pn1 = "%s %s" % (p1.gramps_id, name_displayer.display(p1))
            #pn2 = "%s %s" % (p2.gramps_id, name_displayer.display(p2))
            pn1 = name_displayer.display(p1)
            pn2 = name_displayer.display(p2)
            self.mlist.add([c1, pn1, pn2, c2],(p1key, p2key))

    def do_merge(self, obj):
        store, iter = self.mlist.selection.get_selected()
        if not iter:
            self.infoMsg("Please select a match above")
            return
        (self.p1, self.p2) = self.mlist.get_object(iter)
        self.notImplem("Merge 2 matched persons")
        MergePerson(self.dbstate, self.uistate, self.track, self.p1, self.p2,
                    self.on_update, True)

    def do_automerge(self, obj):
        cutoff = self.automergecutoff.get_model()[self.automergecutoff.get_active()][1]
        msg1 = 'Warning'
        label_msg1 = 'OK'
        label_msg2 = 'NO thanks'
        ant = 0
        matches = []
        #sort by rating = c
        for p1key, p1data in sorted(self.map.items(), key=lambda item: item[1][1], reverse=True):
            if p1key in self.dellist:
                continue
            (p2key, c) = p1data
            if c < cutoff or p2key in self.dellist:
                continue
            if p1key == p2key:
                continue
            matches.append((p1key, p2key))
        msg2 = 'You are about to batch merge %d matches with rating above %s' % (len(matches), cutoff)
        res = QuestionDialog2(msg1, msg2, label_msg1, label_msg2).run()
        if not res: return #False
        for (p1key, p2key) in matches:
            primary = self.dbstate.db.get_person_from_handle(p1key)
            secondary = self.dbstate.db.get_person_from_handle(p2key)
            query = MergePersonQuery(self.dbstate.db, primary, secondary)
            query.execute()
            #Handle names, events: birth, death
            #person = self.dbstate.db.get_person_from_handle(p1key)
        
    def do_comp(self, obj):
        store, iter = self.mlist.selection.get_selected()
        if not iter:
            self.infoMsg("Please select a match above")
            return
        (self.p1, self.p2) = self.mlist.get_object(iter)
        self.uistate.set_active(self.p1, 'Person')
        GraphComparePerson(self.dbstate, self.uistate, self.track, self.p1, self.p2, self.on_update) #FIX

    def on_update(self, handle_list=None):
        if self.db.has_person_handle(self.p1):
            titanic = self.p2
        else:
            titanic = self.p1
        self.dellist.add(titanic)
        self.redraw()

    def update_and_destroy(self, obj):
        self.close()
    
    def close(self, obj, t=None):
        ManagedWindow.close(self, *obj)

    def person_delete(self, handle_list):
        """ deal with person deletes outside of the tool """
        self.dellist.update(handle_list)  #add to dellist
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
        self.update = callback # = tool.on_update
        self.db = dbstate.db
        self.dbstate = dbstate
        self.p1 = p1
        self.p2 = p2

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
        self.show()

    def close(self, obj, t=None):
        ManagedWindow.close(self, *obj)

    def on_help_clicked(self, obj):
        """Display the relevant portion of Gramps manual"""
        #display_help(WIKI_HELP_PAGE , WIKI_HELP_SEC)
        pass

    def ok(self, obj): #RENAME
        MergePerson(self.dbstate, self.uistate, self.track, self.p1, self.p2,
                    self.gr_on_update, True)

    def info(self, *obj):
        print('grinfo button clicked')

    def gr_on_update(self):
        self.close('')

    def update_and_destroy(self, obj):
        self.update(obj)
        self.close()

    #Evt enable and just call close?
    #def person_delete(self, handle_list):
        """ deal with person deletes outside of the tool """
        #self.dellist.update(handle_list)
        #self.redraw()

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

    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

        # Options specific for this report
        self.options_dict = {
            'soundex'   : 0,
            'threshold' : 0.75,
            'algoritm': 'svm',
            'automergecutoff': 0.95
        }
        self.options_help = {
            'soundex'   : ("=0/1","Whether to use SoundEx codes",
                           ["Do not use SoundEx","Use SoundEx"],
                           True),
            'threshold' : ("=num","Threshold for tolerance",
                           "Floating point number")
            }

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
"""graphview compare 2 persons."""

import sys
import os
from re import MULTILINE, findall
from io import StringIO
from subprocess import Popen, PIPE
from xml.parsers.expat import ParserCreate
from html import escape
from collections import defaultdict
from itertools import combinations

#-------------------------------------------------------------------------
#
# GNOME libraries
#
#-------------------------------------------------------------------------
from gi.repository import Gtk, Pango
from gi.repository import GooCanvas
#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.constfunc import win
#-------------------------------------------------------------------------
#
# Fulltextdatabase Whoosh
#
#-------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from ftDatabase import fulltextDatabase

class ViewPersonMatch():
    def __init__(self, dbstate, uistate, canvas, track, p1_handle, p2_handle, callback, matches):
        self.dbstate = dbstate
        self.uistate = uistate
        self.canvas = canvas
        self.dot_data = None
        self.svg_data = None
        self.p1_handle = p1_handle
        self.p2_handle = p2_handle
        self.retest_font = True     # flag indicates need to resize font
        """
        #scrolled_win = Gtk.ScrolledWindow()
        scrolled_win = top.get_object('scrwin')

        scrolled_win.set_shadow_type(Gtk.ShadowType.IN)
        self.hadjustment = scrolled_win.get_hadjustment()
        self.vadjustment = scrolled_win.get_vadjustment()

        self.canvas = GooCanvas.Canvas()
        #self.canvas.connect("scroll-event", self.scroll_mouse)
        self.canvas.props.units = Gtk.Unit.POINTS
        self.canvas.props.resolution_x = 72
        self.canvas.props.resolution_y = 72

        scrolled_win.add(self.canvas)

        self.vbox = Gtk.Box(homogeneous=False, spacing=4,
                            orientation=Gtk.Orientation.VERTICAL)
        self.vbox.set_border_width(4)
        self.toolbar = Gtk.Box(homogeneous=False, spacing=4,
                               orientation=Gtk.Orientation.HORIZONTAL)
        self.vbox.pack_start(self.toolbar, False, False, 0)

        # add zoom-in button
        self.zoom_in_btn = Gtk.Button.new_from_icon_name('zoom-in',
                                                         Gtk.IconSize.MENU)
        self.zoom_in_btn.set_tooltip_text('Zoom in')
        self.toolbar.pack_start(self.zoom_in_btn, False, False, 1)
        self.zoom_in_btn.connect("clicked", self.zoom_in)

        # add zoom-out button
        self.zoom_out_btn = Gtk.Button.new_from_icon_name('zoom-out',
                                                          Gtk.IconSize.MENU)
        self.zoom_out_btn.set_tooltip_text('Zoom out')
        self.toolbar.pack_start(self.zoom_out_btn, False, False, 1)
        self.zoom_out_btn.connect("clicked", self.zoom_out)

        # add original zoom button
        self.orig_zoom_btn = Gtk.Button.new_from_icon_name('zoom-original',
                                                           Gtk.IconSize.MENU)
        self.orig_zoom_btn.set_tooltip_text('Zoom to original')
        self.toolbar.pack_start(self.orig_zoom_btn, False, False, 1)
        self.orig_zoom_btn.connect("clicked", self.set_original_zoom)

        # add best fit button
        self.fit_btn = Gtk.Button.new_from_icon_name('zoom-fit-best',
                                                     Gtk.IconSize.MENU)
        self.fit_btn.set_tooltip_text('Zoom to best fit')
        self.toolbar.pack_start(self.fit_btn, False, False, 1)
        self.fit_btn.connect("clicked", self.fit_to_page)

        # add cancel button
        self.fit_btn = Gtk.Button.new_from_icon_name('cancel',
                                                     Gtk.IconSize.MENU)
        self.fit_btn.set_tooltip_text('CANCEL')
        self.toolbar.pack_start(self.fit_btn, False, False, 1)
        self.fit_btn.connect("clicked", self.cancel)

        self.vbox.pack_start(scrolled_win, True, True, 0)
        """
        # if we have graph lager than graphviz paper size
        # this coef is needed
        self.transform_scale = 1
        self.scale = 1

        # fit the text to boxes
        self.bold_size, self.norm_size = self.fit_text()

        # generate DOT and SVG data
        dot = DotSvgGenerator(self.dbstate, bold_size=self.bold_size, norm_size=self.norm_size)

        graph_data = dot.build_graph(self.p1_handle, self.p2_handle, matches)
        del dot

        if not graph_data:
            # something go wrong when build all-connected tree
            # so turn off this feature
            #self.view._config.set('interface.graphview-show-all-connected', False)
            return

        self.dot_data = graph_data[0]
        self.svg_data = graph_data[1]

        parser = GraphvizSvgParser(self) # , self.view) ??
        parser.parse(self.svg_data)

#        self.animation.update_items(parser.items_list)

        # save transform scale
        self.transform_scale = parser.transform_scale
        self.set_zoom(self.scale)

    def close(self):
        pass # ??

    def zoom_in(self, _button=None):
        """
        Increase zoom scale.
        """
        scale_coef = self.scale * 1.1
        self.set_zoom(scale_coef)

    def zoom_out(self, _button=None):
        """
        Decrease zoom scale.
        """
        scale_coef = self.scale * 0.9
        if scale_coef < 0.01:
            scale_coef = 0.01
        self.set_zoom(scale_coef)

    def set_original_zoom(self, _button):
        """
        Set original zoom scale = 1.
        """
        self.set_zoom(1)

    def set_zoom(self, value):
        """
        Set value for zoom of the canvas widget and apply it.
        """
        self.scale = value
        self.canvas.set_scale(value / self.transform_scale)

    def fit_to_page(self, _button):
        """
        Calculate scale and fit tree to page.
        """
        # get the canvas size
        bounds = self.canvas.get_root_item().get_bounds()
        height_canvas = bounds.y2 - bounds.y1
        width_canvas = bounds.x2 - bounds.x1

        # get scroll window size
        width = self.hadjustment.get_page_size()
        height = self.vadjustment.get_page_size()

        # prevent division by zero
        if height_canvas == 0:
            height_canvas = 1
        if width_canvas == 0:
            width_canvas = 1

        # calculate minimum scale
        scale_h = (height / height_canvas)
        scale_w = (width / width_canvas)
        if scale_h > scale_w:
            scale = scale_w
        else:
            scale = scale_h

        scale = scale * self.transform_scale

        # set scale if it needed, else restore it to default
        if scale < 1:
            self.set_zoom(scale)
        else:
            self.set_zoom(1)

    def fit_text(self):
        """
        Fit the text to the boxes more exactly.  Works by trying some sample
        text, measuring the results, and trying an increasing size of font
        sizes to some sample nodes to see which one will fit the expected
        text size.
        In other words we are telling dot to use different font sizes than
        we are actually displaying, since dot doesn't do a good job of
        determining the text size.
        """
        if not self.retest_font:  # skip this uless font changed.
            return self.bold_size, self.norm_size

        text = "The quick Brown Fox jumped over the Lazy Dogs 1948-01-01."
        dot_test = DotSvgGenerator(self.dbstate) #?? , self.view)
        dot_test.init_dot()
        # These are at the desired font sizes.
        dot_test.generate_node('test_bold', '<B>%s</B>' % text, shape='box')
        dot_test.generate_node('test_norm', text, shape='box')
        # now add nodes at increasing font sizes
        for scale in range(35, 140, 2):
            f_size = dot_test.fontsize * scale / 100.0
            dot_test.generate_node(
                'test_bold' + str(scale),
                '<FONT POINT-SIZE="%(bsize)3.1f"><B>%(text)s</B></FONT>' %
                {'text': text, 'bsize': f_size}, shape='box')
            dot_test.generate_node(
                'test_norm' + str(scale),
                text, shape='box', fontsize=("%3.1f" % f_size))

        # close the graphviz dot code with a brace
        dot_test.write('}\n')

        # get DOT and generate SVG data by Graphviz
        dot_data = dot_test.dot.getvalue().encode('utf8')
        svg_data = dot_test.make_svg(dot_data)
        svg_data = svg_data.decode('utf8')

        # now lest find the box sizes, and font sizes for the generated svg.
        points_a = findall(r'points="(.*)"', svg_data, MULTILINE)
        font_fams = findall(r'font-family="(.*)" font-weight',
                            svg_data, MULTILINE)
        font_sizes = findall(r'font-size="(.*)" fill', svg_data, MULTILINE)
        box_w = []
        for points in points_a:
            box_pts = points.split()
            x_1 = box_pts[0].split(',')[0]
            x_2 = box_pts[1].split(',')[0]
            box_w.append(float(x_1) - float(x_2) - 16)  # adjust for margins

        text_font = font_fams[0] + ", " + font_sizes[0] + 'px'
        font_desc = Pango.FontDescription.from_string(text_font)

        # lets measure the bold text on our canvas at desired font size
        c_text = GooCanvas.CanvasText(parent=self.canvas.get_root_item(),
                                      text='<b>' + text + '</b>',
                                      x=100,
                                      y=100,
                                      anchor=GooCanvas.CanvasAnchorType.WEST,
                                      use_markup=True,
                                      font_desc=font_desc)
        bold_b = c_text.get_bounds()
        # and measure the normal text on our canvas at desired font size
        c_text.props.text = text
        norm_b = c_text.get_bounds()
        # now scan throught test boxes, finding the smallest that will hold
        # the actual text as measured.  And record the dot font that was used.
        for indx in range(3, len(font_sizes), 2):
            if box_w[indx] > bold_b.x2 - bold_b.x1:
                bold_size = float(font_sizes[indx - 1])
                break
        for indx in range(4, len(font_sizes), 2):
            if box_w[indx] > norm_b.x2 - norm_b.x1:
                norm_size = float(font_sizes[indx - 1])
                break
        self.retest_font = False  # we don't do this again until font changes
        # return the adjusted font size to tell dot to use.
        return bold_size, norm_size


    def get_widget(self):
        """
        Return the graph display widget that includes the drawing canvas.
        """
        return self.vbox

    def button_press(self, item, _target, event): #FIX
        return False

    def button_release(self, item, target, event): #FIX
        return False

    def motion_notify_event(self, _item, _target, event): #FIX
        return False

    def select_node(self, item, target, event): #FIX
        """
        Perform actions when a node is clicked.
        If middle mouse was clicked then try to set scroll mode.
        """
        grampsId = item.title #gramps id
        node_class = item.description  # 'node', 'familynode'
        button = event.get_button()[1]  # mouse button 1,2,3
        #Change active for view in main window
        clickedPerson = self.dbstate.db.get_person_from_gramps_id(grampsId)
        self.uistate.set_active(clickedPerson.handle, 'Person')

        return False

#-------------------------------------------------------------------------
#
# GraphvizSvgParser (from GraphView)
#
#-------------------------------------------------------------------------
class GraphvizSvgParser(object):
    """
    Parses SVG produces by Graphviz and adds the elements to a GooCanvas.
    """

    #def __init__(self, widget, view):
    def __init__(self, widget):
        """
        Initialise the GraphvizSvgParser class.
        """
        self.func = None
        self.widget = widget
        self.canvas = widget.canvas
        #self.view = view
        #self.highlight_home_person = self.view._config.get(
        #    'interface.graphview-highlight-home-person')
        #scheme = config.get('colors.scheme')
        #self.home_person_color = config.get('colors.home-person')[scheme]
        self.font_size = 14 #? #self.view._config.get('interface.graphview-font')[1]

        self.tlist = []
        self.text_attrs = None
        self.func_list = []
        self.handle = None
        self.func_map = {"g":       (self.start_g, self.stop_g),
                         "svg":     (self.start_svg, self.stop_svg),
                         "polygon": (self.start_polygon, self.stop_polygon),
                         "path":    (self.start_path, self.stop_path),
                         "image":   (self.start_image, self.stop_image),
                         "text":    (self.start_text, self.stop_text),
                         "ellipse": (self.start_ellipse, self.stop_ellipse),
                         "title":   (self.start_title, self.stop_title)}
        self.text_anchor_map = {"start":  GooCanvas.CanvasAnchorType.WEST,
                                "middle": GooCanvas.CanvasAnchorType.CENTER,
                                "end":    GooCanvas.CanvasAnchorType.EAST}
        # This list is used as a LIFO stack so that the SAX parser knows
        # which Goocanvas object to link the next object to.
        self.item_hier = []

        # list of persons items, used for animation class
        self.items_list = []

        self.transform_scale = 1

    def parse(self, ifile):
        """
        Parse an SVG file produced by Graphviz.
        """
        self.item_hier.append(self.canvas.get_root_item())
        parser = ParserCreate()
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.characters
        parser.Parse(ifile)

        for key in list(self.func_map.keys()):
            del self.func_map[key]
        del self.func_map
        del self.func_list
        del parser

    def start_g(self, attrs):
        """
        Parse <g> tags.
        """
        # The class attribute defines the group type. There should be one
        # graph type <g> tag which defines the transform for the whole graph.
        if attrs.get('class') == 'graph':
            self.items_list.clear()
            transform = attrs.get('transform')
            item = self.canvas.get_root_item()
            transform_list = transform.split(') ')
            scale = transform_list[0].split()
            scale_x = float(scale[0].lstrip('scale('))
            scale_y = float(scale[1])
            self.transform_scale = scale_x
            if scale_x > scale_y:
                self.transform_scale = scale_y
            # scale should be (0..1)
            # fix graphviz issue from version > 2.40.1
            if self.transform_scale > 1:
                self.transform_scale = 1 / self.transform_scale

            item.set_simple_transform(self.bounds[1],
                                      self.bounds[3],
                                      self.transform_scale,
                                      0)
            item.connect("button-press-event", self.widget.button_press)
            item.connect("button-release-event", self.widget.button_release)
            item.connect("motion-notify-event",
                         self.widget.motion_notify_event)
        else:
            item = GooCanvas.CanvasGroup(parent=self.current_parent())
            item.connect("button-press-event", self.widget.select_node)
            self.items_list.append(item)

        item.description = attrs.get('class')
        self.item_hier.append(item)

    def stop_g(self, _tag):
        """
        Parse </g> tags.
        """
        item = self.item_hier.pop()
        item.title = self.handle

    def start_svg(self, attrs):
        """
        Parse <svg> tags.
        """
        GooCanvas.CanvasGroup(parent=self.current_parent())

        view_box = attrs.get('viewBox').split()
        v_left = float(view_box[0])
        v_top = float(view_box[1])
        v_right = float(view_box[2])
        v_bottom = float(view_box[3])
        self.canvas.set_bounds(v_left, v_top, v_right, v_bottom)
        self.bounds = (v_left, v_top, v_right, v_bottom)

    def stop_svg(self, tag):
        """
        Parse </svg> tags.
        """
        pass

    def start_title(self, attrs):
        """
        Parse <title> tags.
        """
        pass

    def stop_title(self, tag):
        """
        Parse </title> tags.
        Stripping off underscore prefix added to fool Graphviz.
        """
        self.handle = tag.lstrip("_")

    def start_polygon(self, attrs):
        """
        Parse <polygon> tags.
        Polygons define the boxes around individuals on the graph.
        """
        coord_string = attrs.get('points')
        coord_count = 5
        points = GooCanvas.CanvasPoints.new(coord_count)
        nnn = 0
        for i in coord_string.split():
            coord = i.split(",")
            coord_x = float(coord[0])
            coord_y = float(coord[1])
            points.set_point(nnn, coord_x, coord_y)
            nnn += 1
        style = attrs.get('style')

        if style:
            p_style = self.parse_style(style)
            stroke_color = p_style['stroke']
            fill_color = p_style['fill']
        else:
            stroke_color = attrs.get('stroke')
            fill_color = attrs.get('fill')

        #if self.handle == self.widget.active_person_handle:
        if (self.handle == self.widget.p1_handle) or (self.handle == self.widget.p2_handle):
            line_width = 3  # thick box
        else:
            line_width = 1  # thin box

        tooltip = str(self.handle) #self.view.tags_tooltips.get(self.handle)

        # highlight the home person
        # stroke_color is not '#...' when tags are drawing, so we check this
        # maybe this is not good solution to check for tags but it works
        #if self.highlight_home_person and stroke_color[:1] == '#':
        #    home_person = self.widget.dbstate.db.get_default_person()
        #    if home_person and home_person.handle == self.handle:
        #        fill_color = self.home_person_color

        item = GooCanvas.CanvasPolyline(parent=self.current_parent(),
                                        points=points,
                                        close_path=True,
                                        fill_color=fill_color,
                                        line_width=line_width,
                                        stroke_color=stroke_color,
                                        tooltip=tooltip)
        # turn on tooltip show if have it
        if tooltip:
            item_canvas = item.get_canvas()
            item_canvas.set_has_tooltip(True)

        self.item_hier.append(item)

    def stop_polygon(self, _tag):
        """
        Parse </polygon> tags.
        """
        self.item_hier.pop()

    def start_ellipse(self, attrs):
        """
        Parse <ellipse> tags.
        These define the family nodes of the graph.
        """
        center_x = float(attrs.get('cx'))
        center_y = float(attrs.get('cy'))
        radius_x = float(attrs.get('rx'))
        radius_y = float(attrs.get('ry'))
        style = attrs.get('style')

        if style:
            p_style = self.parse_style(style)
            stroke_color = p_style['stroke']
            fill_color = p_style['fill']
        else:
            stroke_color = attrs.get('stroke')
            fill_color = attrs.get('fill')

        tooltip = str(self.handle)  #self.view.tags_tooltips.get(self.handle)

        item = GooCanvas.CanvasEllipse(parent=self.current_parent(),
                                       center_x=center_x,
                                       center_y=center_y,
                                       radius_x=radius_x,
                                       radius_y=radius_y,
                                       fill_color=fill_color,
                                       stroke_color=stroke_color,
                                       line_width=1,
                                       tooltip=tooltip)
        if tooltip:
            item_canvas = item.get_canvas()
            item_canvas.set_has_tooltip(True)

        self.current_parent().description = 'familynode'
        self.item_hier.append(item)

    def stop_ellipse(self, _tag):
        """
        Parse </ellipse> tags.
        """
        self.item_hier.pop()

    def start_path(self, attrs):
        """
        Parse <path> tags.
        These define the links between nodes.
        Solid lines represent birth relationships and dashed lines are used
        when a child has a non-birth relationship to a parent. (!! not here from GraphView)
        """
        p_data = attrs.get('d')
        line_width = attrs.get('stroke-width')
        if line_width is None:
            line_width = 1
        line_width = float(line_width)
        style = attrs.get('style')

        if style:
            p_style = self.parse_style(style)
            stroke_color = p_style['stroke']
            is_dashed = 'stroke-dasharray' in p_style
        else:
            stroke_color = attrs.get('stroke')
            is_dashed = attrs.get('stroke-dasharray')

        if is_dashed:
            line_dash = GooCanvas.CanvasLineDash.newv([5.0, 5.0])
            item = GooCanvas.CanvasPath(parent=self.current_parent(),
                                        data=p_data,
                                        stroke_color=stroke_color,
                                        line_width=line_width,
                                        line_dash=line_dash)
        else:
            item = GooCanvas.CanvasPath(parent=self.current_parent(),
                                        data=p_data,
                                        stroke_color=stroke_color,
                                        line_width=line_width)
        self.item_hier.append(item)

    def stop_path(self, _tag):
        """
        Parse </path> tags.
        """
        self.item_hier.pop()

    def start_text(self, attrs):
        """
        Parse <text> tags.
        """
        self.text_attrs = attrs

    def stop_text(self, tag):
        """
        Parse </text> tags.
        The text tag contains some textual data.
        """
        tag = escape(tag)

        pos_x = float(self.text_attrs.get('x'))
        pos_y = float(self.text_attrs.get('y'))
        anchor = self.text_attrs.get('text-anchor')
        style = self.text_attrs.get('style')

        # does the following always work with symbols?
        if style:
            p_style = self.parse_style(style)
            font_family = p_style['font-family']
            text_font = font_family + ", " + p_style['font-size'] + 'px'
        else:
            font_family = self.text_attrs.get('font-family')
            text_font = font_family + ", " + str(self.font_size) + 'px'

        font_desc = Pango.FontDescription.from_string(text_font)

        # set bold text using PangoMarkup
        if self.text_attrs.get('font-weight') == 'bold':
            tag = '<b>%s</b>' % tag

        # text color
        fill_color = self.text_attrs.get('fill')

        GooCanvas.CanvasText(parent=self.current_parent(),
                             text=tag,
                             x=pos_x,
                             y=pos_y,
                             anchor=self.text_anchor_map[anchor],
                             use_markup=True,
                             font_desc=font_desc,
                             fill_color=fill_color)

    def start_image(self, attrs):
        """
        Parse <image> tags.
        """
        pos_x = float(attrs.get('x'))
        pos_y = float(attrs.get('y'))
        width = float(attrs.get('width').rstrip(string.ascii_letters))
        height = float(attrs.get('height').rstrip(string.ascii_letters))
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(attrs.get('xlink:href'))

        item = GooCanvas.CanvasImage(parent=self.current_parent(),
                                     x=pos_x,
                                     y=pos_y,
                                     height=height,
                                     width=width,
                                     pixbuf=pixbuf)
        self.item_hier.append(item)

    def stop_image(self, _tag):
        """
        Parse </image> tags.
        """
        self.item_hier.pop()

    def start_element(self, tag, attrs):
        """
        Generic parsing function for opening tags.
        """
        self.func_list.append((self.func, self.tlist))
        self.tlist = []

        try:
            start_function, self.func = self.func_map[tag]
            if start_function:
                start_function(attrs)
        except KeyError:
            self.func_map[tag] = (None, None)
            self.func = None

    def end_element(self, _tag):
        """
        Generic parsing function for closing tags.
        """
        if self.func:
            self.func(''.join(self.tlist))
        self.func, self.tlist = self.func_list.pop()

    def characters(self, data):
        """
        Generic parsing function for tag data.
        """
        if self.func:
            self.tlist.append(data)

    def current_parent(self):
        """
        Returns the Goocanvas object which should be the parent of any new
        Goocanvas objects.
        """
        return self.item_hier[len(self.item_hier) - 1]

    def parse_style(self, style):
        """
        Parse style attributes for Graphviz version < 2.24.
        """
        style = style.rstrip(';')
        return dict([i.split(':') for i in style.split(';')])

#------------------------------------------------------------------------
#
# DotSvgGenerator (based on GraphView)
#
#------------------------------------------------------------------------

class DotSvgGenerator(object):
    """
    Generator of graphing instructions in dot format and svg data by Graphviz.
    """
    def __init__(self, dbstate, bold_size=0, norm_size=0):
        """
        Initialise the DotSvgGenerator class.
        """
        self.bold_size = bold_size
        self.norm_size = norm_size
        self.dbstate = dbstate
        self.database = dbstate.db
        #self.ftdb = fulltextDatabase(writer=False) # Only used in get_match_color
        self.maxlevel = 2  # 2 generations of Ancestors
        self.minlevel = -2  # 2 generations of Decendants
        self.nodes = []
        self.links = []       # list of (fromId, toId)
        self.dot = None       # will be StringIO()

        #From GraphView?
        # This dictionary contains person handle as the index and the value is
        # the number of families in which the person is a parent. From this
        # dictionary is obtained a list of person handles sorted in decreasing
        # value order which is used to keep multiple spouses positioned
        # together.
        #self.person_handles_dict = {}
        #self.person_handles = []

        # list of persons on path to home person
        #self.current_list = list()
        #self.home_person = None

        # Gtk style context for scrollwindow
        #self.context = self.view.graph_widget.sw_style_context

        # font if we use genealogical symbols
        #self.sym_font = None

    def __del__(self):
        """
        Free stream file on destroy.
        """
        if self.dot:
            self.dot.close()

    def init_dot(self):
        """
        Init/reinit stream for dot file.
        Load and write config data to start of dot file.
        """
        if self.dot:
            self.dot.close()
        self.dot = StringIO()

        #### TODO FIX CONF
        bg_color = '#ffffff'
        font_color = '#000000'
        """
        ###############CONF from GraphView
        # get background color from gtk theme and convert it to hex
        # else use white background
        bg_color = self.context.lookup_color('theme_bg_color')
        if bg_color[0]:
            bg_rgb = (bg_color[1].red, bg_color[1].green, bg_color[1].blue)
            bg_color = rgb_to_hex(bg_rgb)
        else:
            bg_color = '#ffffff'

        # get font color from gtk theme and convert it to hex
        # else use black font
        font_color = self.context.lookup_color('theme_fg_color')
        if font_color[0]:
            fc_rgb = (font_color[1].red, font_color[1].green,
                      font_color[1].blue)
            font_color = rgb_to_hex(fc_rgb)
        else:
            font_color = '#000000'

        # get colors from config
        home_path_color = self.view._config.get(
            'interface.graphview-home-path-color')

        # set of colors
        self.colors = {'link_color':      font_color,
                       'home_path_color': home_path_color}

        # use font from config if needed
        font = self.view._config.get('interface.graphview-font')
        fontfamily = self.resolve_font_name(font[0])
        self.fontsize = font[1]
        ######################CONF
        """

        if not self.bold_size:
            self.bold_size = self.norm_size = 14 #font[1]
        self.arrowheadstyle = 'none'
        self.arrowtailstyle = 'none'
        dpi = 72
        self.fontsize = 14 #?
        fontfamily = False
        font_color = "#2e3436"  #?
        self.spline = 'true'
        rankdir = "TB"
        ratio = "compress"
        ranksep = 5  #self.view._config.get('interface.graphview-ranksep')
        ranksep = ranksep * 0.1
        nodesep = 3  #self.view._config.get('interface.graphview-nodesep')
        nodesep = nodesep * 0.1
        # as we are not using paper,
        # choose a large 'page' size with no margin
        sizew = 100
        sizeh = 100
        xmargin = 0.00
        ymargin = 0.00

        self.write('digraph Compare_matches\n')
        self.write('{\n')
        self.write(' bgcolor="%s";\n' % bg_color)
        self.write(' center="false"; \n')
        self.write(' charset="utf8";\n')
        self.write(' concentrate="true";\n')
        self.write(' dpi="%d";\n' % dpi)
        self.write(' graph [fontsize=%3.1f];\n' % self.fontsize)
        self.write(' margin="%3.2f,%3.2f"; \n' % (xmargin, ymargin))
        self.write(' mclimit="99";\n')
        self.write(' nodesep="%.2f";\n' % nodesep)
        self.write(' outputorder="edgesfirst";\n')
        self.write(' rankdir="%s";\n' % rankdir)
        self.write(' ranksep="%.2f";\n' % ranksep)
        self.write(' ratio="%s";\n' % ratio)
        self.write(' searchsize="100";\n')
        self.write(' size="%3.2f,%3.2f"; \n' % (sizew, sizeh))
        self.write(' splines=%s;\n' % self.spline)
        self.write('\n')
        self.write(' edge [style=solid fontsize=%d];\n' % self.fontsize)

        if fontfamily:
            self.write(' node [style=filled fontname="%s" '
                       'fontsize=%3.1f fontcolor="%s"];\n'
                       % (fontfamily, self.norm_size, font_color))
        else:
            self.write(' node [style=filled fontsize=%3.1f fontcolor="%s"];\n'
                       % (self.norm_size, font_color))
        self.write('\n')
        # clear out lists (see __init__)
        self.nodes = []
        self.links = []

    def resolve_font_name(self, font_name):
        """
        Helps to resolve font by graphviz.
        """
        # Sometimes graphviz have problem with font resolving.
        font_family_map = {"Times New Roman": "Times",
                           "Times Roman":     "Times",
                           "Times-Roman":     "Times",
                           }
        font = font_family_map.get(font_name)
        if font is None:
            font = font_name
        return font

    def generate_node(self, node_id, label, shape="", color="", style="", fillcolor="", url="", fontsize=""):
        """
        Add a node to this graph.
        Nodes can be different shapes like boxes and circles.
        Gramps handles are used as nodes but need to be prefixed with an
        underscore because Graphviz does not like IDs that begin with a number.
        """
        text = '[margin="0.11,0.08"'

        if shape:
            text += ' shape="%s"' % shape

        if color:
            text += ' color="%s"' % color

        if fillcolor:
            text += ' fillcolor="%s"' % fillcolor
            """
            color = hex_to_rgb_float(fillcolor)
            yiq = (color[0] * 299 + color[1] * 587 + color[2] * 114)
            fontcolor = "#ffffff" if yiq < 500 else "#000000"
            text += ' fillcolor="%s" fontcolor="%s"' % (fillcolor, fontcolor)
            """
        if style:
            text += ' style="%s"' % style

        if fontsize:
            text += ' fontsize="%s"' % fontsize
        # note that we always output a label -- even if an empty string --
        # otherwise GraphViz uses the node ID as the label which is unlikely
        # to be what the user wants to see in the graph
        text += ' label=<%s>' % label

        if url:
            text += ' URL="%s"' % url

        text += " ]"
        self.write(' _%s %s;\n' % (node_id.replace('-', '_'), text))

    def get_person_data(self, person):
        if not person: return ('?', '?', '?', '?', '?')
        name = person.get_primary_name().get_name()
        birth_ref = person.get_birth_ref()
        if birth_ref:
            birth = self.database.get_event_from_handle(birth_ref.ref)
            birthDate = birth.get_date_object()
            placeId = birth.get_place_handle()
            if not placeId:
                birthPlace = ""
            else:
                place = self.database.get_place_from_handle(placeId)
                birthPlace = place.get_title()
        else:
            birthDate = ''
            birthPlace = ""
        death_ref = person.get_death_ref()
        if death_ref:
            death = self.database.get_event_from_handle(death_ref.ref)
            deathDate = death.get_date_object()
            placeId = death.get_place_handle()
            if not placeId:
                deathPlace = ""
            else:
                place = self.database.get_place_from_handle(placeId)
                deathPlace = place.get_title()
        else:
            deathDate = ''
            deathPlace = ""
        return (name, birthDate, birthPlace.replace('församling', ''), deathDate, deathPlace.replace('församling', ''))

    """
    def get_match_color(self, handle1, handle2):
        # for links between matched pairs of persons
        if not handle1 or not handle2: return "#ffffff"  # white
        if handle1 == handle2: return "#00ff00"  # green
        score = 0.0
        hits = self.ftdb.getMatchesForHandle(handle1)
        for h in hits:
            if h['grampsHandle'] == handle2:
                score = h['score']
                break
        (kred, mred, kgreen, mgreen) = (-2550.0, 2422.5, 1020.0, -510.0)
        red = int(kred * score + mred)
        if red > 255: red = 255
        elif red < 0: red = 0
        green = int(kgreen * score + mgreen)
        if green > 255: green = 255
        elif green < 0: green = 0
        return "#%02x%02x10" % (red, green)
    """
    
    def person_node(self, p, color):
        (name, birthDate, birthPlace, deathDate, deathPlace) = self.get_person_data(p)
        rows = '<TR><TD><B>%s</B></TD></TR>' % name
        rows += '<TR><TD>ID: %s</TD></TR>' % p.gramps_id
        rows += '<TR><TD>b. %s</TD></TR>' % birthDate
        rows += '<TR><TD>%s</TD></TR>' % birthPlace
        rows += '<TR><TD>d. %s</TD></TR>' % deathDate
        rows += '<TR><TD>%s</TD></TR>' % deathPlace
        label = '<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" CELLBORDER="0">%s</TABLE>' % rows
        self.generate_node(p.gramps_id, label, shape='box', fillcolor=color)

    def family_node(self, family, color):
        date = '-'
        for event_ref in family.get_event_ref_list():
            event = self.database.get_event_from_handle(event_ref.ref)
            if event.get_type().is_marriage():
                date = event.get_date_object()
                break                
        options = 'margin="0.11,0.08" shape="ellipse" color="#cccccc" fillcolor="%s" fontcolor="#000000" style="filled"' % color
        label = "ID:%s, m. %s" % (family.gramps_id, date)
        self.generate_node(family.gramps_id, label, shape='ellipse', fillcolor=color)

    def generate_link(self, from_node, to_node, constraint=False, style='solid', color="#2e3436", penwidth=1):
        opt = 'style=%s arrowhead=none arrowtail=none color="%s" penwidth="%d"' % (style, color, penwidth)
        if constraint:
            opt += " constraint=false"
        self.write('  _%s -> _%s [%s];\n' % (from_node.replace('-', '_'), to_node.replace('-', '_'), opt))

    def add_family(self, person, family, updown):
        self.nodes.append(('family', None, family, self.color))
        if updown == 'up':
            self.links.append((family.gramps_id, person.gramps_id))
        else:
            self.links.append((person.gramps_id, family.gramps_id))

    def add_parents(self, person, family_handle, level):
        family = self.database.get_family_from_handle(family_handle)
        self.add_family(person, family, 'up')
        handle = family.get_father_handle()
        if handle:
            p = self.database.get_person_from_handle(handle)
            self.nodes.append(('person', level, p, self.color))
            self.links.append((p.gramps_id, family.gramps_id))
            if self.maxlevel > level:
                for f_handle in p.get_parent_family_handle_list(): #Fam where p is child
                    self.add_parents(p, f_handle, level + 1)
        handle = family.get_mother_handle()
        if handle:
            p = self.database.get_person_from_handle(handle)
            self.nodes.append(('person', level, p, self.color))
            self.links.append((p.gramps_id, family.gramps_id))
            if self.maxlevel > level:
                for f_handle in p.get_parent_family_handle_list(): #Fam where p is child
                    self.add_parents(p, f_handle, level + 1)

    def add_spouse(self, person, family, level):
        self.add_family(person, family, 'down')
        spouse_handle = family.get_father_handle()
        if spouse_handle == person.handle:
            spouse_handle = family.get_mother_handle()
        if spouse_handle:
            p = self.database.get_person_from_handle(spouse_handle)
            self.links.append((person.gramps_id, p.gramps_id)) #Make invisible FIX
            self.nodes.append(('person', level, p, self.color))
            self.links.append((p.gramps_id, family.gramps_id))
            #spouse parents
            for family_handle in p.get_parent_family_handle_list(): #Fam where p (spouse) is child
                #get_main_parents_family_handle??
                self.add_parents(p, family_handle, level + 1)

    def add_children(self, family, level):
        # children of family
        for child_ref in family.get_child_ref_list():
            child = self.database.get_person_from_handle(child_ref.ref)
            self.nodes.append(('person', level, child, self.color))
            self.links.append((family.gramps_id, child.gramps_id))
            if level > self.minlevel:
                for family_handle in child.get_family_handle_list(): #Fam where child parent or spouse
                    fam = self.database.get_family_from_handle(family_handle)
                    self.add_family(child, fam, 'down')
                    self.add_children(fam, level - 1)
    
    def build_graph(self, p1_handle, p2_handle, matches):
        """
        Builds a GraphViz tree based on comparing p_handle1, p_handle2
        """
        # reinit dot file stream (write starting graphviz dot code to file)
        self.init_dot()
        level = 0
        
        p1 = self.database.get_person_from_handle(p1_handle)
        p2 = self.database.get_person_from_handle(p2_handle)
        
        matchColor = '#bed6dc' #green for main match
        self.color =  '#a5cafb' #Blue for p1
        for p in (p1, p2):
            level = 0
            self.nodes.append(('person', level, p, matchColor))
            for family_handle in p.get_parent_family_handle_list(): #Fam where p is child
                #get_main_parents_family_handle??
                self.add_parents(p, family_handle, level + 1)
            # Family of p (spouse, children)
            for family_handle in p.get_family_handle_list(): #Fam where p parent or spouse
                fam = self.database.get_family_from_handle(family_handle)
                self.add_family(p, fam, 'down')
                self.add_spouse(p, fam, level) #adds spouse parents
                self.add_children(fam, level - 1)

            self.color = '#cc997f' #Brown for p2
        done = []
        rank = defaultdict(list)
        allNodes = set()
        for (typ, level, node, color) in self.nodes:
            if node.gramps_id in done: continue
            done.append(node.gramps_id)
            if typ == 'family':
                self.family_node(node, color)
            elif typ == 'person':
                self.person_node(node, color)
                allNodes.add(node.gramps_id)
                rank[level].append(node.gramps_id.replace('-', '_'))
            #else: ERROR
        for (l, nodeIds) in rank.items():
            self.write("{rank = same; _%s;}\n" % '; _'.join(nodeIds))
        #links
        done = []
        for (nodeId1, nodeId2) in self.links:
            if (nodeId1, nodeId2) in done: continue
            self.generate_link(nodeId1, nodeId2)
            done.append((nodeId1, nodeId2))
        #links between matches
        matchpair2rating = {}
        for (c, p1id, p2id) in matches:
            matchpair2rating[(p1id, p2id)] = c
            matchpair2rating[(p2id, p1id)] = c
        for pair in combinations(allNodes, 2):
            if pair in matchpair2rating:
                # color dep on rating 1.0 = grön, 0.75=yellow, 0.5=red
                rating = matchpair2rating[pair]
                green = int(255 * (rating - 0.5) / 0.5)
                red = 255 - green
                color = "#%s" % bytearray([red, green, 0]).hex()
                if p1.gramps_id in pair and p2.gramps_id in pair:
                    constraint = False
                else:
                    constraint = True
                self.generate_link(pair[0], pair[1], constraint=constraint, style='dashed', color=color, penwidth=5)

        # close the graphviz dot code with a brace
        self.write('}\n')

        # get DOT and generate SVG data by Graphviz
        dot_data = self.dot.getvalue().encode('utf8')
        svg_data = self.make_svg(dot_data)
        return (dot_data, svg_data)

    def make_svg(self, dot_data):
        """
        Make SVG data by Graphviz.
        """
        if win():
            svg_data = Popen(['dot', '-Tsvg'],
                             creationflags=DETACHED_PROCESS,
                             stdin=PIPE,
                             stdout=PIPE,
                             stderr=PIPE).communicate(input=dot_data)[0]
        else:
            svg_data = Popen(['dot', '-Tsvg'],
                             stdin=PIPE,
                             stdout=PIPE).communicate(input=dot_data)[0]
        return svg_data

    def write(self, text):
        """
        Write text to the dot file.
        """
        if self.dot:
            self.dot.write(text)

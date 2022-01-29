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
from gramps.gui.managedwindow import ManagedWindow
from gramps.gen.constfunc import win
#-------------------------------------------------------------------------
#
# Fulltextdatabase Whoosh
#
#-------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from ftDatabase import fulltextDatabase

#class ViewPersonMatch(ManagedWindow): INTE ManagedWindow
class ViewPersonMatch():
    def __init__(self, dbstate, uistate, canvas, track, p1_handle, p2_handle, callback):
        #ManagedWindow.__init__(self, uistate, track, self.__class__)
        self.dbstate = dbstate
        self.uistate = uistate
        self.canvas = canvas
        self.dot_data = None
        self.svg_data = None
        self.p1_handle = p1_handle
        self.p2_handle = p2_handle
        self.retest_font = True     # flag indicates need to resize font
        #print('View',  self.p1_handle,  self.p2_handle)
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

        graph_data = dot.build_graph(self.p1_handle, self.p2_handle)
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

#    def cancel(self, *obj):
#        ManagedWindow.close(self, *obj)

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
        dot_test.add_node('test_bold', '<B>%s</B>' % text, shape='box')
        dot_test.add_node('test_norm', text, shape='box')
        # now add nodes at increasing font sizes
        for scale in range(35, 140, 2):
            f_size = dot_test.fontsize * scale / 100.0
            dot_test.add_node(
                'test_bold' + str(scale),
                '<FONT POINT-SIZE="%(bsize)3.1f"><B>%(text)s</B></FONT>' %
                {'text': text, 'bsize': f_size}, shape='box')
            dot_test.add_node(
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
        return False

#-------------------------------------------------------------------------
#
# GraphvizSvgParser
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
        when a child has a non-birth relationship to a parent.
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

# AA0 start
#------------------------------------------------------------------------
#
# TreeNode and Tree
#    Used to build compare graph
#
#------------------------------------------------------------------------
class TreeNode:
    def __init__(self, person_handle, level=0):
        self.families = {} # key family_handle; content set of handles for
                           #         'spouses', 'children', 'parents'
        self.fathers = []
        self.mothers = []
        self.parents = []    # list of Node
        self.spouses = []    # list of Node
        self.children = []   # list of Node
        self.person_handle = person_handle
        self.level = level

    # Insert Nodes
    def insertFather(self, person_handle, family_handle):
        p_node = self.insertParent(person_handle, family_handle)
        self.fathers.append(person_handle)
        return p_node

    def insertMother(self, person_handle, family_handle):
        p_node = self.insertParent(person_handle, family_handle)
        self.mothers.append(person_handle)
        return p_node

    def insertParent(self, person_handle, family_handle):
        parent_node = TreeNode(person_handle, self.level + 1)
        self.parents.append(parent_node)
        if family_handle not in self.families:
            self.families[family_handle] ={'spouses': set(), 'children': set(), 'parents': set()}
        self.families[family_handle]['parents'].add(person_handle)
        return parent_node

    def insertSpouse(self, person_handle, family_handle):
        spouse_node = TreeNode(person_handle, self.level)
        self.spouses.append(spouse_node)
        if family_handle not in self.families:
            self.families[family_handle] ={'spouses': set(), 'children': set(), 'parents': set()}
        self.families[family_handle]['spouses'].add(person_handle)
        return spouse_node

    def insertChild(self, person_handle, family_handle):
        child_node = TreeNode(person_handle, self.level - 1)
        self.children.append(child_node)
        if family_handle not in self.families:
            self.families[family_handle] ={'spouses': set(), 'children': set(), 'parents': set()}
        self.families[family_handle]['children'].add(person_handle)
        return child_node

class Tree:
    def __init__(self, db, ancestor_generations=2):
        self.db = db
        self.id_list = set() # (id, level) id is handle prepended with either 'P' or 'F' ?? FIX!!
        self.links = set() # (from_id, to_id, clusterid)
        self.cluster_cnt = 1 # Use as unique id for clusters
        self.main_person_handle = None
        self.main_person_treenode = None
        self.ancestor_generations = 2 # FIX ancestor_generations

    def BuildTree(self, person_handle):
        self.main_person_handle = person_handle
        self.id_list.add((self.main_person_handle, 0))
        self.main_person_treenode = TreeNode(person_handle)
        self.populateTreeAncestors(self.main_person_treenode, 1)  # ancestors
        # Add families (spouse and children) only for main person
        person = self.db.get_person_from_handle(self.main_person_handle)
        for family_handle in person.get_family_handle_list():
            family = self.db.get_family_from_handle(family_handle)
            if family:
                self.links.add((self.main_person_handle, family_handle, "Cluster_%s" % self.main_person_handle)) # person -> family
                # from find_children
                for child_ref in family.get_child_ref_list():
                    self.main_person_treenode.insertChild(child_ref.ref, family_handle)
                    self.id_list.add((child_ref.ref, -1))
                    self.id_list.add((family_handle, None))
                    self.links.add((family_handle, child_ref.ref, None)) # family -> child
                # Spouses
                m_handle = family.get_mother_handle()
                if m_handle and m_handle != self.main_person_handle:
                    self.main_person_treenode.insertSpouse(m_handle, family_handle)
                    self.id_list.add((m_handle, 0))
                    self.id_list.add((family_handle, None))
                    self.links.add((m_handle, family_handle, "Cluster_%s" % self.main_person_handle)) # parent -> family
                f_handle = family.get_father_handle()
                if f_handle and f_handle != self.main_person_handle:
                    self.main_person_treenode.insertSpouse(f_handle, family_handle)
                    self.id_list.add((f_handle, 0))
                    self.id_list.add((family_handle, None))
                    self.links.add((f_handle, family_handle, "Cluster_%s" % self.main_person_handle)) # parent -> family

    def populateTreeAncestors(self, treenode, level):
        if level >= self.ancestor_generations: return
        handle = treenode.person_handle
        person = self.db.get_person_from_handle(handle)
        cl_handle = "cluster_%d" % self.cluster_cnt
        self.cluster_cnt += 1
        for family_handle in person.get_parent_family_handle_list():
            family = self.db.get_family_from_handle(family_handle)
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            if father_handle:
                 p_node = treenode.insertFather(father_handle, family_handle)
                 self.id_list.add((father_handle, level))
                 self.id_list.add((family_handle, None))
                 self.links.add((father_handle, family_handle, cl_handle)) # parent -> family
                 self.links.add((family_handle, handle, None)) # family -> person
                 self.populateTreeAncestors(p_node, level + 1)
            if mother_handle:
                 p_node = treenode.insertMother(mother_handle, family_handle)
                 self.id_list.add((mother_handle, level))
                 self.id_list.add((family_handle, None))
                 self.links.add((mother_handle, family_handle, cl_handle)) # parent -> family
                 self.links.add((family_handle, handle, None)) # family -> person
                 self.populateTreeAncestors(p_node, level + 1)

    def get_id_list(self):
        return self.id_list

    def get_link_list(self):
        return self.links

#------------------------------------------------------------------------
#
# DotSvgGenerator
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
        #self.uistate = view.uistate
        self.database = dbstate.db
        self.ftdb = fulltextDatabase(writer=False)
        #self.view = view

        self.dot = None         # will be StringIO()

        # This dictionary contains person handle as the index and the value is
        # the number of families in which the person is a parent. From this
        # dictionary is obtained a list of person handles sorted in decreasing
        # value order which is used to keep multiple spouses positioned
        # together.
        self.person_handles_dict = {}
        self.person_handles = []

        # list of persons on path to home person
        self.current_list = list()
        self.home_person = None

        # Gtk style context for scrollwindow
        #self.context = self.view.graph_widget.sw_style_context

        # font if we use genealogical symbols
        self.sym_font = None

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
        ###############CONF
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
        pagedir = "BL"
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

        self.write('digraph GRAMPS_graph\n')
        self.write('{\n')
        self.write(' bgcolor="%s";\n' % bg_color)
        self.write(' center="false"; \n')
        self.write(' charset="utf8";\n')
        self.write(' concentrate="false";\n')
        self.write(' dpi="%d";\n' % dpi)
        self.write(' graph [fontsize=%3.1f];\n' % self.fontsize)
        self.write(' margin="%3.2f,%3.2f"; \n' % (xmargin, ymargin))
        self.write(' mclimit="99";\n')
        self.write(' nodesep="%.2f";\n' % nodesep)
        self.write(' outputorder="edgesfirst";\n')
        self.write(' pagedir="%s";\n' % pagedir)
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
        #self.uistate.connect('font-changed', self.font_changed)
        #self.symbols = Symbols()
        #self.font_changed()

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

    def add_node(self, node_id, label, shape="", color="",
                 style="", fillcolor="", url="", fontsize=""):
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
        self.write(' _%s %s;\n' % (node_id, text))

    def getPairs(self, group1, group2):
        pairs = set()
        if len(group1) == 1 and len(group2) == 1:
            pairs.add((group1[0], group2[0]))
        elif len(group1) >= 1 and len(group2) == 0:
            for spouse in group1:
                pairs.add((spouse, None))
        elif len(group1) == 0 and len(group2) >= 1:
            for spouse in group2:
                pairs.add((None, spouse))
        elif len(group1) == 0 and len(group2) == 0:
            pass
        else:
            #NOT IMPLEMENTED
            print(group1)
            print(group2)
            print('Multiple persons in group - not implemented!')
            # FIX handle error
            sys.exit()
        return pairs

    def get_person_data(self, person):
        #OLD  if not handle: return ('-', '-', '-', '-', '-')
        #OLD  person = self.database.get_person_from_handle(handle)
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

    def get_match_color(self, handle1, handle2):
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

    def handle_pair(self, cmp_id, handle1, handle2, main=False):
        (name1, birthDate1, birthPlace1, deathDate1, deathPlace1) = self.get_person_data(handle1)
        (name2, birthDate2, birthPlace2, deathDate2, deathPlace2) = self.get_person_data(handle2)
        color = self.get_match_color(handle1, handle2)
        options = 'margin="0.11,0.08" shape="box" color="#1f4986" fillcolor="%s" fontcolor="#000000" style="solid, filled"' % color
        row1 = '<TR><TD></TD><TD><B>%s</B></TD><TD><B>%s</B></TD></TR>' % (name1, name2)
        row2 = '<TR><TD ROWSPAN="2">b.</TD><TD>%s</TD><TD>%s</TD></TR>' % (birthDate1, birthDate2)
        row3 = '<TR><TD>%s</TD><TD>%s</TD></TR>' % (birthPlace1, birthPlace2)
        row4 = '<TR><TD ROWSPAN="2">d.</TD><TD>%s</TD><TD>%s</TD></TR>' % (deathDate1, deathDate2)
        row5 = '<TR><TD>%s</TD><TD>%s</TD></TR>' % (deathPlace1, deathPlace2)
        if handle1 == handle2:
            row2 = '<TR><TD colspan="3">SAME</TD></TR>'
            table = '<TABLE BORDER="3" CELLSPACING="0" CELLPADDING="1" CELLBORDER="1">%s%s</TABLE>' % (row1, row2)
        elif main:
            table = '<TABLE BORDER="3" CELLSPACING="0" CELLPADDING="1" CELLBORDER="1">%s%s%s%s%s</TABLE>' % (row1, row2, row3, row4, row5)
        else:
            table = '<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="1" CELLBORDER="1">%s%s%s%s%s</TABLE>' % (row1, row2, row3, row4, row5)
        label = 'label=<%s>' % table
        txt = ' %s [ %s label=<%s> ];\n' % (cmp_id, options, table)
        self.write(txt)

    def handle_family(self, id):
        #txt = ' %s [margin="0.11,0.08" shape="ellipse" color="#cccccc" fillcolor="#eeeeee" fontcolor="#000000" style="filled" label=<<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" CELLBORDER="0"><TR><TD>%s</TD></TR></TABLE>> ];\n' % (id, 'Marr')
        options = 'margin="0.11,0.08" shape="ellipse" color="#cccccc" fillcolor="#eeeeee" fontcolor="#000000" style="filled"'
        (tmp, fam_handle) = id.split('_')
        family = self.database.get_family_from_handle(fam_handle)
        self.show_full_dates = True
        #self.show_places = True
        #label = self.get_family_label(family)
        label = '<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" CELLBORDER="0"><TR><TD>FAM</TD></TR></TABLE>' #TMP FIX
        txt = ' %s [%s label=<%s> ];\n' % (id, options, label)
        self.write('%s\n' % txt)

    def handle_link(self, from_id, to_id):
        txt = '  %s -> %s  [ style=solid arrowhead=none arrowtail=none color="#2e3436" ];\n' % (from_id, to_id)
        self.write('%s\n' % txt)

    def genDotCmp(self, tree1, tree2):
        """
            generate dot-code for two trees compared
        """
        nodeMap = {}
        cmp_cnt = 1
        # main pair
        cmp_id = "cmp_%d" % cmp_cnt
        self.handle_pair(cmp_id, tree1.main_person_handle, tree2.main_person_handle, main=True)
        nodeMap[tree1.main_person_handle] = cmp_id
        nodeMap[tree2.main_person_handle] = cmp_id
        cmp_cnt += 1
        # spouses
        spouses1 = [x.person_handle for x in tree1.main_person_treenode.spouses]
        spouses2 = [x.person_handle for x in tree2.main_person_treenode.spouses]
        for pair in self.getPairs(spouses1, spouses2):
            cmp_id = "cmp_%d" % cmp_cnt
            self.handle_pair(cmp_id, pair[0], pair[1])
            nodeMap[pair[0]] = cmp_id
            nodeMap[pair[1]] = cmp_id
            cmp_cnt += 1
        # children
        children1 = tree1.main_person_treenode.children
        children2 = tree2.main_person_treenode.children
        #   sort by birth(year) - see old RGD
        # pair children
        # Test just do simple pairs
        for child in children1 + children2:
            cmp_id = "cmp_%d" % cmp_cnt
            self.handle_pair(cmp_id, child.person_handle, None)
            nodeMap[child.person_handle] = cmp_id
            cmp_cnt += 1
        #end Test
        # parents
        fathers1 = tree1.main_person_treenode.fathers
        fathers2 = tree2.main_person_treenode.fathers
        for pair in self.getPairs(fathers1, fathers2):
            cmp_id = "cmp_%d" % cmp_cnt
            self.handle_pair(cmp_id, pair[0], pair[1])
            nodeMap[pair[0]] = cmp_id
            nodeMap[pair[1]] = cmp_id
            cmp_cnt += 1
        mothers1 = tree1.main_person_treenode.mothers
        mothers2 = tree2.main_person_treenode.mothers
        for pair in self.getPairs(mothers1, mothers2):
            cmp_id = "cmp_%d" % cmp_cnt
            self.handle_pair(cmp_id, pair[0], pair[1])
            nodeMap[pair[0]] = cmp_id
            nodeMap[pair[1]] = cmp_id
            cmp_cnt += 1

        #recurse for parent parents ? FIX ancestor_generations ?

        # map ids in links
        # create family nodes
        done_families = []
        for (from_id, to_id, cluster) in tree1.get_link_list().union(tree2.get_link_list()):
            # ignore cluster for the time beeing
            try:
                from_id = nodeMap[from_id]
            except:
                from_id = "F_%s" % from_id
                if from_id not in done_families:
                    self.handle_family(from_id)
                    done_families.append(from_id)
            try:
                to_id = nodeMap[to_id]
            except:
                to_id = "F_%s" % to_id
                if to_id not in done_families:
                    self.handle_family(to_id)
                    done_families.append(to_id)
            self.handle_link(from_id, to_id)
        return

    # AA0 new code end

    # AA0 changed to generate compare graph: active_person -> p_handle1, p_handle2
    def OLDbuild_graph(self, p_handle1, p_handle2):  # active_person):
        """
        Builds a GraphViz tree based on comparing p_handle1, p_handle2
        """
        # reinit dot file stream (write starting graphviz dot code to file)
        self.init_dot()

        tree1 = Tree(self.database)
        tree1.BuildTree(p_handle1)
        tree2 = Tree(self.database)
        tree2.BuildTree(p_handle2)

        self.genDotCmp(tree1, tree2)

        # close the graphviz dot code with a brace
        self.write('}\n')

        # get DOT and generate SVG data by Graphviz
        dot_data = self.dot.getvalue().encode('utf8')
        svg_data = self.make_svg(dot_data)

        return (dot_data, svg_data)

    def person_node(self, p):
        (name, birthDate, birthPlace, deathDate, deathPlace) = self.get_person_data(p)
        row1 = '<TR><TD>%s <B>%s</B></TD></TR>' % (p.gramps_id, name)
        row2 = '<TR><TD>%s</TD></TR>' % birthDate
        row3 = '<TR><TD>%s</TD></TR>' % birthPlace
        row4 = '<TR><TD>%s</TD></TR>' % deathDate
        row5 = '<TR><TD>%s</TD></TR>' % deathPlace
        label = '<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" CELLBORDER="0">%s%s%s%s%s</TABLE>' % (row1, row2, row3, row4, row5)
        self.add_node(p.gramps_id, label, shape='box', fillcolor=self.color)

    def family_node(self, family):
        #update to use add_node FIX
        #options = 'margin="0.11,0.08" shape="ellipse" color="#cccccc" fillcolor="#eeeeee" fontcolor="#000000" style="filled"'
        options = 'margin="0.11,0.08" shape="ellipse" color="#cccccc" fillcolor="%s" fontcolor="#000000" style="filled"' % self.color
        label = '<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" CELLBORDER="0"><TR><TD>%s</TD></TR></TABLE>' % family.gramps_id
        txt = ' _%s [%s label=<%s> ];\n' % (family.gramps_id, options, label)
        self.write('%s\n' % txt)

    def add_link(self, from_node, to_node):
        txt = '  _%s -> _%s  [ style=solid arrowhead=none arrowtail=none color="#2e3436" ];\n' % (from_node, to_node)
        self.write('%s\n' % txt)

    def build_graph(self, p1_handle, p2_handle):  # active_person):
        """
        Builds a GraphViz tree based on comparing p_handle1, p_handle2
        """
        # reinit dot file stream (write starting graphviz dot code to file)
        self.init_dot()
        self.color = '#bed6dc' #green for main match
        done = []
        p1 = self.database.get_person_from_handle(p1_handle)
        self.person_node(p1)
        done.append(p1.gramps_id)
        p2 = self.database.get_person_from_handle(p2_handle)
        self.person_node(p2)
        done.append(p2.gramps_id)
        self.write('subgraph TMP1{ style="invis";')
        self.add_link(p1.gramps_id, p2.gramps_id)
        self.write('{rank = same; _%s; _%s;}\n' % (p1.gramps_id, p2.gramps_id))
        self.write('}\n')
        self.color =  '#a5cafb' #Blue for p1
        for p in (p1, p2):
            for family_handle in p.get_family_handle_list():
                fam = self.database.get_family_from_handle(family_handle)
                if fam.gramps_id in done: continue
                self.family_node(fam)
                done.append(fam.gramps_id)
                father_handle = fam.get_father_handle()
                if father_handle:
                    father = self.database.get_person_from_handle(father_handle)
                    if father.gramps_id not in done:
                        self.person_node(father)
                        done.append(father.gramps_id)
                if father_handle and father: self.add_link(father.gramps_id, fam.gramps_id)

                mother_handle = fam.get_mother_handle()
                if mother_handle:
                    mother = self.database.get_person_from_handle(mother_handle)
                    if mother.gramps_id not in done:
                        self.person_node(mother)
                        done.append(mother.gramps_id)
                if mother_handle and mother: self.add_link(mother.gramps_id, fam.gramps_id)

                for child_ref in fam.get_child_ref_list():
                    child = self.database.get_person_from_handle(child_ref.ref)
                    if child.gramps_id not in done:
                        self.person_node(child)
                        done.append(child.gramps_id)
                    self.add_link(fam.gramps_id, child.gramps_id)
            self.color = '#cc997f' #Brown for p2

        # close the graphviz dot code with a brace
        self.write('}\n')

        # get DOT and generate SVG data by Graphviz
        dot_data = self.dot.getvalue().encode('utf8')
        svg_data = self.make_svg(dot_data)
        #print(dot_data)
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
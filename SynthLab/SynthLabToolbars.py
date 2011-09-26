import gtk
import common.Config as Config

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from gettext import gettext as _


def main_toolbar_common(toolbar, synthLab):

        def _button_factory(name='', toolbar=None, cb=None, arg=None,
                            tooltip=None, toggle=True):
            ''' Add a toggle button to a toolbar '''
            if toggle:
                button = ToggleToolButton(name)
            else:
                button = ToolButton(name)
            if cb is not None:
                if arg is None:
                    button.connect('clicked', cb)
                else:
                    button.connect('clicked', cb, arg)
            if toolbar is not None:
                toolbar.insert(button, -1)
            button.show()
            if tooltip is not None:
                button.set_tooltip(tooltip)
            return button

        def _insertSeparator(toolbar, x=1):
            for i in range(x):
                separator = gtk.SeparatorToolItem()
                separator.set_draw(False)
                toolbar.insert(separator, -1)
                separator.show()

        def _label_factory(label='', toolbar=None):
            ''' Add a label to a toolbar '''
            mylabel = gtk.Label(label)
            mytool = gtk.ToolItem()
            mytool.add(mylabel)
            mylabel.show()
            if toolbar is not None:
                toolbar.insert(mytool, -1)
            mytool.show()
            return mylabel

        def _slider_factory(toolbar=None, cb=None, tooltip=None):
            ''' Add a slider to a toolbar '''
            sliderAdj = gtk.Adjustment(2, .5, 30, .01, .01, 0)
            sliderAdj.connect("value_changed", cb)
            slider = gtk.HScale(adjustment=sliderAdj)
            slider.set_size_request(250,15)
            slider.set_inverted(False)
            slider.set_value_pos(gtk.POS_RIGHT)
            sliderTool = gtk.ToolItem()
            sliderTool.add(slider)
            sliderTool.show()
            tooltips = gtk.Tooltips()
            sliderTool.set_tooltip(tooltips, tooltip)
            toolbar.insert(sliderTool, -1)
            slider.show()
            return sliderAdj

        durationSliderLabel = _label_factory(label=_('Duration:  '),
                                             toolbar=toolbar)

        durationSliderAdj = _slider_factory(toolbar=toolbar,
                                            cb=synthLab.handleDuration,
                                            tooltip=_('Duration'))

        durationSliderLabelSecond = _label_factory(label=_(' s.'),
                                                   toolbar=toolbar)

        _insertSeparator(toolbar, 1)

        resetButton = _button_factory(
            name='edit-clear',
            toolbar=toolbar,
            cb=synthLab.handleReset,
            tooltip=_('Reset the worktable'),
            toggle=False)

        return durationSliderAdj


class mainToolbar(gtk.Toolbar):
    def __init__(self, toolbox, synthLab):
        gtk.Toolbar.__init__(self)

        self.durationSliderAdj = main_toolbar_common(self, synthLab)


class recordToolbar(gtk.Toolbar):
    def __init__(self, toolbox, synthLab):
        gtk.Toolbar.__init__(self)

        def _button_factory(name='', toolbar=None, cb=None, arg=None,
                            tooltip=None, toggle=True):
            ''' Add a toggle button to a toolbar '''
            if toggle:
                button = ToggleToolButton(name)
            else:
                button = ToolButton(name)
            if cb is not None:
                if arg is None:
                    button.connect('clicked', cb)
                else:
                    button.connect('clicked', cb, arg)
            if toolbar is not None:
                toolbar.insert(button, -1)
            button.show()
            if tooltip is not None:
                button.set_tooltip(tooltip)
            return button

        def _insertSeparator(x=1):
            for i in range(x):
                self.separator = gtk.SeparatorToolItem()
                self.separator.set_draw(False)
                self.insert(self.separator, -1)
                self.separator.show()

        self.toolbox = toolbox
        self.synthLab = synthLab

        if Config.FEATURES_LAB:
            self.synthRecButtons = []
            for i in range(6):
                j = i + 1
                self.synthRecButton.append(_button_factory(
                        name='rec%d' % (j),
                        toolbar=self,
                        cb=self.synthLab.recordSound,
                        arg=j,
                        tooltip=_('Record Synth sound into slot') + \
                            ' "lab%d"' % (j)))

        if False: #Config.FEATURES_OGG:
            # Disabled .ogg support until fixing #2669
            #RecordOgg button
            self.recordOggButton = _button_factory(
                name='record0',
                toolbar=self,
                cb=self.synthLab.recordOgg,
                tooltip=_('Record to ogg'))


class presetToolbar(gtk.Toolbar):
    def __init__(self,toolbox, synthLab):
        gtk.Toolbar.__init__(self)

        def _insertSeparator(x = 1):
            for i in range(x):
                self.separator = gtk.SeparatorToolItem()
                self.separator.set_draw(False)
                self.insert(self.separator,-1)
                self.separator.show()

        def _radio_button_factory(name='', toolbar=None, cb=None, arg=None,
                                  tooltip=None, group=None):
            ''' Add a radio button to a toolbar '''
            button = RadioToolButton(group=group)
            button.set_named_icon(name)
            if cb is not None:
                if arg is None:
                    button.connect('clicked', cb)
                else:
                    button.connect('clicked', cb, arg)
            if toolbar is not None:
                toolbar.insert(button, -1)
            button.show()
            if tooltip is not None:
                button.set_tooltip(tooltip)
            return button

        self.toolbox = toolbox
        self.synthLab = synthLab

        self.presetButton = []
        for i in range(10):
            j = i + 1
            if i == 0:
                self.presetButton.append(_radio_button_factory(
                        name='preset%d' % (j),
                        toolbar=self,
                        cb=self.synthLab.presetCallback,
                        arg=j,
                        tooltip=_('Preset') + ' %d' % (j),
                        group=None))
            else:
                self.presetButton.append(_radio_button_factory(
                        name='preset%d' % (j),
                        toolbar=self,
                        cb=self.synthLab.presetCallback,
                        arg=j,
                        tooltip=_('Preset') + ' %d' % (j),
                        group=self.presetButton[0]))

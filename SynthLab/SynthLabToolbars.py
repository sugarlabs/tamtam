import gtk
import common.Config as Config

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from gettext import gettext as _


class mainToolbar(gtk.Toolbar):
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

        def _label_factory(label='', toolbar=None):
            mylabel = gtk.Label(label)
            mytool = gtk.ToolItem()
            mytool.add(mylabel)
            if toolbar is not None:
                toolbar.insert(mytool, -1)
            return mylabel

        self.toolbox = toolbox
        self.synthLab = synthLab

        self.tooltips = gtk.Tooltips()

        self.durationSliderLabel = _label_factory(label=_('Duration:  '),
                                                  toolbar=self)

        self.durationSliderAdj = gtk.Adjustment(2, .5, 30, .01, .01, 0)
        self.durationSliderAdj.connect("value_changed",
                                       self.synthLab.handleDuration)
        self.durationSlider = gtk.HScale(adjustment=self.durationSliderAdj)
        self.durationSlider.set_size_request(250,15)
        self.durationSlider.set_inverted(False)
        self.durationSlider.set_value_pos(gtk.POS_RIGHT)
        self.durationSliderTool = gtk.ToolItem()
        self.durationSliderTool.add(self.durationSlider)
        self.durationSliderTool.show()
        self.durationSliderTool.set_tooltip(self.tooltips, _('Duration'))
        self.insert(self.durationSliderTool, -1)
        self.durationSlider.show()

        self.durationSliderLabelSecond = _label_factory(label=_(' s.'),
                                                        toolbar=self)

        _insertSeparator(1)

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

        _insertSeparator(1)

        self.resetButton = _button_factory(
            name='sl-reset',
            toolbar=self,
            cb=self.synthLab.handleReset,
            tooltip=_('Reset the worktable'),
            toggle=False)


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
            ''' Add a toggle button to a toolbar '''
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
                self.presetButton.append(RadioToolButton(
                        name='preset%d' % (j)
                        toolbar=self,
                        cb=self.synthLab.presetCallback,
                        arg=j,
                        tooltip=_('Preset') + ' %d' % (j),
                        group=None))
            else:
                self.presetButton.append(RadioToolButton(
                        name='preset%d' % (j)
                        toolbar=self,
                        cb=self.synthLab.presetCallback,
                        arg=j,
                        tooltip=_('Preset') + ' %d' % (j),
                        group=self.presetButton[0]))

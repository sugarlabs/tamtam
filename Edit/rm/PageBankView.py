from gi.repository import Gtk, Gdk

from GUI.GUIConstants import GUIConstants
from GUI.Core.PageView import PageView

class PageBankView( Gtk.Frame ):

    NO_PAGE = -1

    def __init__( self, selectPageCallback, pageDropCallback ):
        Gtk.Frame.__init__( self )
        self.grid = Gtk.Grid.new()
        self.add( self.grid )
        self.drag_dest_set( Gtk.DestDefault.ALL, [ Gtk.TargetEntry.new( "tune page", Gtk.TargetFlags.SAME_APP, 11 )], Gdk.DragAction.COPY|Gdk.DragAction.MOVE )
        self.connect( "drag_data_received", self.dragDataReceived )
        self.selectPageCallback = selectPageCallback
        self.pageDropCallback = pageDropCallback
        self.selectedPageIds = set([])
        self.pageIndexDictionary = {}
        self.pageViews = {}

    def dragDataReceived( self, widget, context, x, y, selectionData, info, time):
        self.pageDropCallback( selectionData.data )
        
    def addPage( self, pageId, invokeCallback = True ):
        pageIndex = len( self.pageViews.keys() )
        self.pageIndexDictionary[ pageIndex ] = pageId
        
        #TODO: resize table to suit number of pages?
        #if pageIndex > ( self.table.n-rows * self.table.n_columns ):
        #    self.table.resize( self.table.n_rows + 1, self.table.n_columns )

        pageView = PageView( pageIndex, self.selectPage, True )
        self.pageViews[ pageIndex ] = pageView
            
        columnIndex = pageIndex % GUIConstants.NUMBER_OF_PAGE_BANK_COLUMNS
        rowIndex = int( pageIndex / GUIConstants.NUMBER_OF_PAGE_BANK_COLUMNS )
        self.grid.attach( pageView, columnIndex, rowIndex, columnIndex + 1, rowIndex + 1)
        self.updateSize( pageView )
        
        pageView.drag_source_set( Gdk.ModifierType.BUTTON1_MASK, 
                                  [ ( "bank page", Gtk.TargetFlags.SAME_APP, 10 ) ],
                                  Gdk.DragAction.COPY )
        
        self.selectPage( pageId, True, invokeCallback )
        
        pageView.show()
            
    def set_size_request( self, width, height ):
        Gtk.Frame.set_size_request( self, width, height )
        self.grid.set_size_request( width, height )
        for pageId in self.pageViews.keys():
            self.updateSize( self.pageViews[ pageId ] )
            
    def updateSize( self, pageView ):
        pageView.set_size_request( self.get_allocation().width / GUIConstants.NUMBER_OF_PAGE_BANK_COLUMNS,
                                   GUIConstants.PAGE_HEIGHT - 1 )
    
    def selectPage( self, selectedPageId, invokeCallback = True, deselectOthers = True ):
        if deselectOthers:
            for pageId in self.pageViews.keys():
                self.pageViews[ pageId ].setSelected( pageId == selectedPageId )
                if pageId != selectedPageId:
                    self.selectedPageIds.discard( pageId )
                else:
                    self.selectedPageIds.add( pageId )
                #nb: pageId might be NO_PAGE, and selectedPageIds can be empty here
            
        else:
            self.pageViews[ selectedPageId ].toggleSelected()
            if self.pageViews[ selectedPageId ].selected:
                self.selectedPageIds.add( selectedPageId )
            else:
                self.selectedPageIds.discard( selectedPageId )
            
        if invokeCallback:
            self.selectPageCallback( selectedPageId )
            
    def getSelectedPageIds( self ):
        rval =  filter( lambda id: self.pageViews[id].selected == True, self.pageViews.keys())
        return rval


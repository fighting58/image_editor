import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QAction, QFileDialog, QTreeView, QFileSystemModel, QSplitter,
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QListWidget, QListWidgetItem,
                             QColorDialog, QInputDialog, QComboBox,QMenu, QToolBar)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QMouseEvent, QCursor, QIcon, QFontDatabase, QKeyEvent
from PyQt5.QtCore import Qt, QSize, QRectF, QSizeF, pyqtSignal, QPointF, QSortFilterProxyModel, QRegExp

class Layer:
    def __init__(self, pixmap=None):
        self.pixmap = pixmap
        self.lines = []
        self.texts = []

class TextItem:
    def __init__(self, text, position, font, color):
        self.text = text
        self.position = position
        self.current_font = font
        self.color = color
        self.rect = None
        self.is_selected = False

class LineItem:
    def __init__(self, start, end, mid, color, is_dashed):
        self.start = start
        self.mid = mid
        self.end = end
        self.color = color
        self.is_dashed = is_dashed
        self.is_selected = False

class MyListWidget(QListWidget):
    item_moved = pyqtSignal(int, int)  # 시그널: (from_index, to_index)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setEditTriggers(QListWidget.DoubleClicked | QListWidget.EditKeyPressed)

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if item:
            self.setCurrentItem(item)
            
            menu = QMenu(self)
            move_up_action = QAction("위로 이동", self)
            move_down_action = QAction("아래로 이동", self)
            edit_action = QAction("편집", self)
            remove_action = QAction("제거", self)
            
            menu.addAction(move_up_action)
            menu.addAction(move_down_action)
            menu.addAction(edit_action)
            menu.addAction(remove_action)
            
            move_up_action.triggered.connect(self.move_item_up)
            move_down_action.triggered.connect(self.move_item_down)
            edit_action.triggered.connect(self.edit_current_item)
            remove_action.triggered.connect(self.remove_current_item)
            
            menu.exec_(self.mapToGlobal(position))

    def move_item_up(self):
        current_row = self.currentRow()
        if current_row > 0:
            self.move_item(current_row, current_row - 1)

    def move_item_down(self):
        current_row = self.currentRow()
        if current_row < self.count() - 1:
            self.move_item(current_row, current_row + 1)

    def move_item(self, from_index, to_index):
        item = self.takeItem(from_index)
        self.insertItem(to_index, item)
        self.setCurrentItem(item)
        self.item_moved.emit(from_index, to_index)

    def edit_current_item(self):
        current_item = self.currentItem()
        if current_item:
            current_item.setFlags(current_item.flags() | Qt.ItemIsEditable)
            self.editItem(current_item)

    def remove_current_item(self):
        current_row = self.currentRow()
        if current_row != -1:
            self.takeItem(current_row)
            self.item_moved.emit(current_row, -1)  # -1 indicates removal

    def add_item(self, text):
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.addItem(item)
        self.item_moved.emit(-1, self.count() - 1)  # -1 as from_index indicates new item

class EditableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.lineEdit().returnPressed.connect(self.on_return_pressed)

    def on_return_pressed(self):
        if self.currentText().isdigit():
            size = int(self.currentText())
            if 1 <= size <= 1000:  # 적절한 폰트 크기 범위 설정
                if self.findText(self.currentText()) == -1:
                    self.addItem(self.currentText())
                self.setCurrentIndex(self.findText(self.currentText()))
            else:
                self.setCurrentIndex(self.findText(str(self.parent().current_font.pointSize())))
        else:
            self.setCurrentIndex(self.findText(str(self.parent().current_font.pointSize())))

class ImageFileFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        if self.sourceModel().isDir(index):
            return True
        file_name = self.sourceModel().fileName(index)
        return bool(QRegExp.match(r".*\.(jpg|jpeg|png)$", file_name, QRegExp.IGNORECASE))

class ImageExplorerWidget(QWidget):
    # Define a custom signal that emits the file path as a string
    fileDoubleClicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.splitter = QSplitter(self)
        self.layout.addWidget(self.splitter)

        self.model = QFileSystemModel()
        self.model.setRootPath('')

        self.proxyModel = ImageFileFilterProxyModel()
        self.proxyModel.setSourceModel(self.model)
        self.proxyModel.setFilterKeyColumn(0)  # Apply filter on the file names

        self.tree = QTreeView()
        self.tree.setModel(self.proxyModel)
        self.tree.setRootIndex(self.proxyModel.mapFromSource(self.model.index('')))
        self.tree.setColumnWidth(0, 400)

        # Hide other columns except the first one (name)
        for i in range(1, self.model.columnCount()):
            self.tree.hideColumn(i)

        self.tree.doubleClicked.connect(self.onDoubleClick)

        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setMinimumSize(1, 1)

        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.imageLabel)

    def onDoubleClick(self, index):
        # Map the proxy index to the source index
        source_index = self.proxyModel.mapToSource(index)
        file_path = self.model.filePath(source_index)
        self.fileDoubleClicked.emit(file_path)

class ImageEditor(QMainWindow):
    IMAGE_SIZE = (800, 600)
    def __init__(self):
        super().__init__()
        self.layers = []
        self.current_layer = None
        self.drawing = False
        self.adding_text = False
        self.moving_text = False
        self.selected_text = None
        self.selected_texts = set()
        self.selected_line = None
        self.moving_vertex = None
        self.points = []
        self.temp_line = None
        self.line_color = QColor(Qt.blue)
        self.current_font_color = QColor(Qt.blue)
        self.current_font = QFont("굴림", pointSize=12, weight=1)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('이미지 편집기')

        # 툴바 생성
        self.toolbar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # 툴바 아이콘 추가
        new_action = QAction(QIcon('icons/file.svg'), '새 문서', self)
        new_action.triggered.connect(self.new_document)
        self.toolbar.addAction(new_action)

        open_action = QAction(QIcon('icons/book-open.svg'), '열기', self)
        open_action.triggered.connect(self.open_image)
        self.toolbar.addAction(open_action)

        save_action = QAction(QIcon('icons/save.svg'), '저장', self)
        save_action.triggered.connect(self.save_image)
        self.toolbar.addAction(save_action)

        self.toolbar.addSeparator()

        self.font_family_combo = QComboBox(self)
        self.font_family_combo.addItems(self.get_korean_fonts())
        self.font_family_combo.setCurrentText("굴림")
        self.font_family_combo.currentTextChanged.connect(self.change_font_family)
        self.toolbar.addWidget(self.font_family_combo)

        # 폰트 크기 콤보 박스 추가
        self.font_size_combo = EditableComboBox(self)
        self.font_size_combo.addItems(['7', '8', '9', '10', '11', '12', '14', '16'])
        self.font_size_combo.setCurrentText(str(self.current_font.pointSize()))
        self.font_size_combo.currentTextChanged.connect(self.change_font_size)
        self.toolbar.addWidget(self.font_size_combo)

        # 폰트 스타일 서브메뉴 생성
        font_style_menu = QMenu('폰트 스타일', self)
        self.font_style_action = QAction("가", self)
        self.font_style_action.setFont(QFont(self.current_font.family(), pointSize=12))
        self.font_style_action.setMenu(font_style_menu)
        
        normal_action = QAction('Normal', self)
        bold_action = QAction('Bold', self)
        italic_action = QAction('Italic', self)
        bold_italic_action = QAction('Bold Italic', self)

        normal_action.triggered.connect(lambda: self.change_font_style("Normal"))
        bold_action.triggered.connect(lambda: self.change_font_style("Bold"))
        italic_action.triggered.connect(lambda: self.change_font_style("Italic"))
        bold_italic_action.triggered.connect(lambda: self.change_font_style("Bold Italic"))

        font_style_menu.addAction(normal_action)
        font_style_menu.addAction(bold_action)
        font_style_menu.addAction(italic_action)
        font_style_menu.addAction(bold_italic_action)

        self.toolbar.addAction(self.font_style_action)

        self.font_color_btn = QPushButton("T")
        self.font_color_btn.setFixedSize(QSize(24, 24))
        self.font_color_btn.setFont(QFont("Courier", 18, weight=QFont.Bold))
        self.font_color_btn.setToolTip('글자 색상')
        self.font_color_btn.setStyleSheet(f"color: {self.current_font_color.name()}")
        self.font_color_btn.clicked.connect(self.change_font_color)
        self.toolbar.addWidget(self.font_color_btn)

        self.toolbar.addSeparator()

        self.line_type_combo = QComboBox(self)
        self.line_type_combo.addItems(["────", "─ ─ ─"])
        self.line_type_combo.setCurrentText("─ ─ ─")
        self.line_type_combo.currentIndexChanged.connect(self.change_line_type)
        self.toolbar.addWidget(self.line_type_combo)

        self.line_color_menubtn = QPushButton("L")
        self.line_color_menubtn.setFixedSize(QSize(24, 24))
        self.line_color_menubtn.setFont(QFont("Courier", 18, weight=QFont.Bold))
        self.line_color_menubtn.setToolTip('라인 색상')
        self.line_color_menubtn.setStyleSheet(f"color: {self.line_color.name()}")
        self.line_color_menubtn.clicked.connect(self.change_line_color)
        self.toolbar.addWidget(self.line_color_menubtn)

        self.toolbar.addSeparator()

        line_drawing_action = QAction(QIcon('icons/pen-tool.svg'), '거리 기입', self)
        line_drawing_action.triggered.connect(self.start_drawing_line)
        self.toolbar.addAction(line_drawing_action)        

        adding_text_action = QAction(QIcon('icons/type.svg'), '텍스트 입력', self)
        adding_text_action.triggered.connect(self.start_adding_text)
        self.toolbar.addAction(adding_text_action)   

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 상단 컨트롤 영역
        controls_layout = QHBoxLayout()
        # 레이어 컨트롤
        layer_layout = QVBoxLayout()
        self.layer_list = MyListWidget()
        self.layer_list.itemClicked.connect(self.select_layer)
        self.layer_list.item_moved.connect(self.update_items)
        add_layer_btn = QPushButton('레이어 추가')
        add_layer_btn.clicked.connect(lambda: self.add_layer(pixmap=None))
        layer_layout.addWidget(self.layer_list)
        layer_layout.addWidget(add_layer_btn)
        
        controls_layout.addLayout(layer_layout)
        
        # 이미지 편집 영역
        editor_layout = QHBoxLayout()
        self.image_label = QLabel()
        self.image_label.setFixedSize(*self.IMAGE_SIZE)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid black;")
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.mousePressEvent
        self.image_label.mouseMoveEvent = self.mouseMoveEvent
        editor_layout.addWidget(self.image_label)
        
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(editor_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('파일')

        open_action = QAction('열기', self)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

        save_action = QAction('내보내기', self)
        save_action.triggered.connect(self.save_image)
        file_menu.addAction(save_action)

        self.image_label.mouseDoubleClickEvent = self.mouseDoubleClickEvent
        self.image_label.mouseReleaseEvent = self.mouseReleaseEvent

        # 키 이벤트를 처리하기 위해 포커스 정책 설정
        self.setFocusPolicy(Qt.StrongFocus)

    # 새로운 메서드들
    def new_document(self):
        self.layers = []
        self.layer_list.clear()
        self.current_layer = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete:
            self.delete_selected_items()

    def delete_selected_items(self):
        if self.current_layer:
            # 선택된 선 삭제
            if self.selected_line:
                self.current_layer.lines.remove(self.selected_line)
                self.selected_line = None

            # 선택된 텍스트 삭제
            for text in list(self.selected_texts):
                if text in self.current_layer.texts:
                    self.current_layer.texts.remove(text)
            self.selected_texts.clear()

    def change_font_family(self):
        font_family = self.font_family_combo.currentText()
        self.current_font.setFamily(font_family)
        self.update_toolbar()
        self.update_selected_text_style()

    def update_toolbar(self):
        current_font = self.current_font
        current_font.setPointSize(12)
        self.font_style_action.setFont(QFont(current_font))

    def change_font_size(self, size):
        try:
            new_size = int(size)
            if 1 <= new_size <= 50:  # 적절한 폰트 크기 범위 설정
                self.current_font.setPointSize(new_size)
                self.update_selected_text_style()
            else:
                self.font_size_combo.setCurrentText(str(self.current_font.pointSize()))
        except ValueError:
            self.font_size_combo.setCurrentText(str(self.current_font.pointSize()))

    def get_korean_fonts(self):
        korean_fonts= []
        font_db = QFontDatabase()
        fonts = font_db.families()
        for font in fonts:
            writing_systems = font_db.writingSystems(font)
            for ws in writing_systems:
                if ws == QFontDatabase.Korean:
                    korean_fonts.append(font)
        return korean_fonts

    def change_font_style(self, style):        
        if style == "Bold":
            self.current_font.setBold(True)
            self.current_font.setItalic(False)
        elif style == "Italic":
            self.current_font.setBold(False)
            self.current_font.setItalic(True)
        elif style == "Bold Italic":
            self.current_font.setBold(True)
            self.current_font.setItalic(True)
        else:  # Normal
            self.current_font.setBold(False)
            self.current_font.setItalic(False)

        self.update_toolbar()        
        self.update_selected_text_style()

    def update_selected_text_style(self):
        if not self.selected_texts:
            return
        for text_item in self.selected_texts:
            text_item.current_font = QFont(self.current_font)
            text_item.color = QColor(self.current_font_color)

    def open_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "이미지 열기", "", "이미지 파일 (*.png *.jpg *.bmp *.jpeg)")
        if file_name:
            pixmap = QPixmap(file_name)
            scaled_pixmap = self.scale_pixmap(pixmap)
            self.add_layer(scaled_pixmap)

    def save_image(self):
        if not self.layers:
            return
        self.unselect()
        file_name, _ = QFileDialog.getSaveFileName(self, "이미지 저장", "", "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)")
        if file_name:
            self.image_label.pixmap().save(file_name, quality=50)

    def scale_pixmap(self, pixmap):
        return pixmap.scaled(QSize(*self.IMAGE_SIZE), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def add_layer(self, pixmap=None):
        if pixmap is None:
            pixmap = QPixmap(*self.IMAGE_SIZE)
            pixmap.fill(Qt.transparent)
        layer = Layer(pixmap=pixmap)
        self.layers.append(layer)
        self.layer_list.addItem(f"레이어 {len(self.layers)}")
        if len(self.layer_list) > 1:
            self.layer_list.move_item(len(self.layer_list)-1, 0)
        self.current_layer = layer

    def select_layer(self, item):
        index = self.layer_list.row(item)
        if 0 <= index < len(self.layers):
            self.current_layer = self.layers[index]

    def start_drawing_line(self):
        self.drawing = True
        self.points = []
        self.temp_line = None
        # self.add_line_btn.setText('선 그리는 중... (3점 선택)')

    def start_adding_text(self):
        self.adding_text = True
        # self.add_text_btn.setText('텍스트 위치 선택...')
    
    def change_font_color(self):
        color = QColorDialog.getColor(initial=self.line_color)
        if color.isValid():
            self.current_font_color = color
            self.font_color_btn.setStyleSheet(f"color: {color.name()};")
        self.update_selected_text_style()

    def update_items(self, from_index, to_index):
        if from_index == -1:  # 새 아이템 추가
            self.add_layer()
        elif to_index == -1:  # 아이템 제거
            del self.layers[from_index]
        else:  # 아이템 이동
            item = self.layers.pop(from_index)
            self.layers.insert(to_index, item)

    def mousePressEvent(self, event: QMouseEvent):
        if self.drawing:
            self.points.append(event.pos())
            if len(self.points) == 3:
                text, ok = QInputDialog.getText(self, "텍스트 입력", "텍스트:")
                if ok:
                    line_type = self.line_type_combo.currentText()
                    new_line = LineItem(self.points[0], self.points[1], self.points[2], QColor(self.line_color), line_type=="─ ─ ─")
                    self.current_layer.lines.append(new_line)
                    self.current_layer.texts.append(TextItem(text, self.points[2], QFont(self.current_font), QColor(self.current_font_color)))
                    self.update_image()
                self.drawing = False
                self.points = []
                self.temp_line = None
                # self.add_line_btn.setText('거리 기입')
                self.update_image()
        elif self.adding_text:
            text, ok = QInputDialog.getText(self, "텍스트 입력", "텍스트:")
            self.unselect()
            if ok and text:
                self.current_layer.texts.append(TextItem(text, event.pos(), self.current_font, self.current_font_color))
                self.update_image()
            self.adding_text = False
            # self.add_text_btn.setText('텍스트 추가')
        else:
            # 선 선택 로직
            for layer in self.layers:
                for line in layer.lines:
                    if self.is_near_line(event.pos(), line):
                        self.unselect()  # 기존 선택 해제
                        self.selected_line = line
                        self.selected_line.is_selected = True
                        self.moving_vertex = self.get_nearest_vertex(event.pos(), line)
                        self.update_image()
                        return
            
            # 텍스트 선택 로직
            for layer in self.layers:
                for text_item in layer.texts:
                    if text_item.rect and text_item.rect.contains(event.pos()):
                        if not (event.modifiers() & Qt.ControlModifier):
                            self.unselect()  # Ctrl 키가 눌리지 않았다면 기존 선택 해제
                        self.selected_text = text_item
                        self.add_selected_text(text_item)
                        self.moving_text = True
                        self.offset = event.pos() - text_item.position
                        self.update_image()
                        return            
            self.unselect()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drawing:
            if len(self.points) == 1:
                self.temp_line = (self.points[0], event.pos())
            elif len(self.points) == 2:
                self.temp_line = (self.points[0], event.pos(), self.points[1])
        elif self.moving_text and self.selected_text:
            new_pos = event.pos() - self.offset
            self.selected_text.position = new_pos
        elif self.selected_line and self.moving_vertex:
            new_pos = event.pos()
            if self.moving_vertex == 'start':
                self.selected_line.start = new_pos
            elif self.moving_vertex == 'mid':
                self.selected_line.mid = new_pos
            elif self.moving_vertex == 'end':
                self.selected_line.end = new_pos
        self.update_image()        
        self.update_cursor(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.moving_text:
            self.moving_text = False
        if self.selected_line:
            self.moving_vertex = None
        self.update_image()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        for layer in self.layers:
            for text_item in layer.texts:
                if text_item.rect and text_item.rect.contains(event.pos()):
                    new_text, ok = QInputDialog.getText(self, "텍스트 수정", "새 텍스트:", text=text_item.text)
                    if ok:
                        text_item.text = new_text
                    return

    def unselect(self):
        self.selected_texts.clear()
        if self.selected_line:
            self.selected_line.is_selected = False
            self.selected_line = None
    
    def add_selected_text(self, text):
        self.selected_texts.add(text)
        self.update_image()

    def is_near_line(self, point, line, threshold=5):
        return (self.point_to_line_distance(point, line.start, line.mid) < threshold or
                self.point_to_line_distance(point, line.mid, line.end) < threshold)

    def point_to_line_distance(self, point, line_start, line_end):
        p = QPointF(point)
        a = QPointF(line_start)
        b = QPointF(line_end)
        ap = p - a
        ab = b - a
        proj = QPointF.dotProduct(ap, ab) / QPointF.dotProduct(ab, ab)
        proj = max(0, min(1, proj))
        closest = a + proj * ab
        return (p - closest).manhattanLength()

    def get_nearest_vertex(self, point, line):
        distances = [
            (point - line.start).manhattanLength(),
            (point - line.mid).manhattanLength(),
            (point - line.end).manhattanLength()
        ]
        min_distance = min(distances)
        if min_distance == distances[0]:
            return 'start'
        elif min_distance == distances[1]:
            return 'mid'
        else:
            return 'end'

    def change_line_color(self):
        color = QColorDialog.getColor(initial=self.line_color)
        if color.isValid():
            self.line_color = color
            self.line_color_menubtn.setStyleSheet(f"color: {color.name()};")
        for layer in self.layers:
            for line in layer.lines:
                if line.is_selected:
                    line.color = color
    
    def change_line_type(self):
        is_dashed = self.line_type_combo.currentText() == "─ ─ ─"
        if self.selected_line:
            self.selected_line.is_dashed = is_dashed

    def initialize_pixmap(self):
        result = QPixmap(*self.IMAGE_SIZE)
        result.fill(Qt.transparent)
        self.image_label.setPixmap(result)

    def update_image(self):
        if not self.layers:
            self.initialize_pixmap()
            return
        
        result = QPixmap(*self.IMAGE_SIZE)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        
        for layer in self.layers[::-1]:
            painter.setOpacity(0.8)
            painter.drawPixmap(0, 0, layer.pixmap)            
            
            for line in layer.lines:
                pen = QPen(line.color)
                if line.is_dashed:
                    pen.setStyle(Qt.DashLine)
                if line.is_selected:
                    pen.setWidth(3)
                painter.setPen(pen)
                painter.drawLine(line.start, line.mid)
                painter.drawLine(line.mid, line.end)
                
                if line.is_selected:
                    painter.setBrush(Qt.red)
                    painter.drawEllipse(line.start, 5, 5)
                    painter.drawEllipse(line.mid, 5, 5)
                    painter.drawEllipse(line.end, 5, 5)
            
            for text_item in layer.texts:
                painter.setFont(text_item.current_font)
                painter.setPen(text_item.color)
                text_rect = painter.boundingRect(QRectF(text_item.position, QSizeF()), Qt.AlignLeft, text_item.text)
                painter.drawText(text_rect, text_item.text)
                text_item.rect = text_rect
                
                if text_item in self.selected_texts:
                    painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
                    painter.drawRect(text_rect)
        
        if self.temp_line:
            painter.setPen(QPen(self.line_color))
            if len(self.temp_line) == 2:
                painter.drawLine(self.temp_line[0], self.temp_line[1])
            elif len(self.temp_line) == 3:
                painter.drawLine(self.temp_line[0], self.temp_line[1])
                painter.drawLine(self.temp_line[1], self.temp_line[2])
        
        painter.end()
        self.image_label.setPixmap(result)

    def update_cursor(self, pos):
        if self.selected_line:
            if self.is_near_vertex(pos, self.selected_line.start) or \
               self.is_near_vertex(pos, self.selected_line.mid) or \
               self.is_near_vertex(pos, self.selected_line.end):
                self.setCursor(Qt.CrossCursor)
                return
        
        for layer in self.layers:
            for text_item in layer.texts:
                if text_item.rect and text_item.rect.contains(pos):
                    self.setCursor(Qt.SizeAllCursor)
                    return
        
        self.setCursor(Qt.ArrowCursor)

    def is_near_vertex(self, point, vertex, threshold=5):
        return (point - vertex).manhattanLength() < threshold

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageEditor()
    ex.show()
    sys.exit(app.exec_())
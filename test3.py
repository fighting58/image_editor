import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QAction, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QListWidget, QListWidgetItem,
                             QColorDialog, QInputDialog, QComboBox,QMenu, QToolBar)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QMouseEvent, QCursor, QIcon, QFontDatabase
from PyQt5.QtCore import Qt, QSize, QRectF, QSizeF, pyqtSignal

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
        self.toolbar.addWidget(self.line_type_combo)

        self.line_color_menubtn = QPushButton("L")
        self.line_color_menubtn.setFixedSize(QSize(24, 24))
        self.line_color_menubtn.setFont(QFont("Courier", 18, weight=QFont.Bold))
        self.line_color_menubtn.setToolTip('라인 색상')
        self.line_color_menubtn.setStyleSheet(f"color: {self.line_color.name()}")
        self.line_color_menubtn.clicked.connect(self.change_line_color)
        self.toolbar.addWidget(self.line_color_menubtn)

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

        # 입력 컨트롤
        edit_layout = QVBoxLayout()
        self.add_line_btn = QPushButton('거리 기입')
        self.add_line_btn.clicked.connect(self.start_drawing_line)
        self.add_text_btn = QPushButton('텍스트 추가')
        self.add_text_btn.clicked.connect(self.start_adding_text)
        edit_layout.addWidget(self.add_line_btn)
        edit_layout.addWidget(self.add_text_btn)
        
        controls_layout.addLayout(layer_layout)
        controls_layout.addLayout(edit_layout)
        
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

    # 새로운 메서드들
    def new_document(self):
        self.layers = []
        self.layer_list.clear()
        self.current_layer = None
        self.update_image()

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
        self.update_image()

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
        self.update_image()

    def select_layer(self, item):
        index = self.layer_list.row(item)
        if 0 <= index < len(self.layers):
            self.current_layer = self.layers[index]

    def start_drawing_line(self):
        self.drawing = True
        self.points = []
        self.temp_line = None
        self.add_line_btn.setText('선 그리는 중... (3점 선택)')

    def start_adding_text(self):
        self.adding_text = True
        self.add_text_btn.setText('텍스트 위치 선택...')
    
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
        self.update_image()

    def mousePressEvent(self, event: QMouseEvent):
        if self.drawing:
            self.points.append(event.pos())
            if len(self.points) == 3:
                text, ok = QInputDialog.getText(self, "텍스트 입력", "텍스트:")
                if ok:
                    line_type = self.line_type_combo.currentText()
                    self.current_layer.lines.append((self.points[0], self.points[1], self.points[2], QColor(self.line_color), line_type=="─ ─ ─"))
                    self.current_layer.texts.append(TextItem(text, self.points[2], QFont(self.current_font), QColor(self.current_font_color)))
                    self.update_image()
                self.drawing = False
                self.points = []
                self.temp_line = None
                self.add_line_btn.setText('거리 기입')
                self.update_image()
        elif self.adding_text:
            text, ok = QInputDialog.getText(self, "텍스트 입력", "텍스트:")
            self.unselect()
            if ok and text:
                self.current_layer.texts.append(TextItem(text, event.pos(), self.current_font, self.current_font_color))
                self.update_image()
            self.adding_text = False
            self.add_text_btn.setText('텍스트 추가')
        else:
            # Check if a text item is clicked
            for layer in self.layers:
                for text_item in layer.texts:
                    if text_item.rect and text_item.rect.contains(event.pos()):
                        self.selected_text = text_item
                        self.add_selected_text(text_item)
                        self.moving_text = True
                        self.offset = event.pos() - text_item.position
                        return
                self.selected_text = None
            self.unselect()

    def unselect(self):
        self.selected_texts = set()
        self.update_image()
    
    def add_selected_text(self, text):
        self.selected_texts.add(text)
        self.update_image()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drawing:
            if len(self.points) == 1:
                self.temp_line = (self.points[0], event.pos())
            elif len(self.points) == 2:
                self.temp_line = (self.points[0], event.pos(), self.points[1])
            self.update_image()
        elif self.moving_text and self.selected_text:
            new_pos = event.pos() - self.offset
            self.selected_text.position = new_pos
            self.update_image()
        self.update_cursor(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.moving_text:
            self.moving_text = False
            self.update_image()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        for layer in self.layers:
            for text_item in layer.texts:
                if text_item.rect and text_item.rect.contains(event.pos()):
                    new_text, ok = QInputDialog.getText(self, "텍스트 수정", "새 텍스트:", text=text_item.text)
                    if ok:
                        text_item.text = new_text
                        self.update_image()
                    return

    def change_line_color(self):
        color = QColorDialog.getColor(initial=self.line_color)
        if color.isValid():
            self.line_color = color
            self.line_color_menubtn.setStyleSheet(f"color: {color.name()};")

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
            
            for start, end, mid, color, is_dashed in layer.lines:
                pen = QPen(color)
                if is_dashed:
                    pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
                painter.drawLine(start, mid)
                painter.drawLine(mid, end)
            
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
        for layer in self.layers:
            for text_item in layer.texts:
                if text_item.rect and text_item.rect.contains(pos):
                    self.setCursor(Qt.SizeAllCursor)
                    return
        self.setCursor(Qt.ArrowCursor)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageEditor()
    ex.show()
    sys.exit(app.exec_())
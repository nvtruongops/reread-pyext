"""Small built-in interface translations for the supported desktop languages."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)


_LANGUAGE = "vi"

_ENGLISH = {
    "Gỡ cài đặt re/read": "Uninstall re/read",
    "Gỡ ứng dụng cùng lịch sử, cài đặt và toàn bộ mô hình đã tải.": "Remove the app, history, settings, and all downloaded models.",
    "Gỡ cài đặt": "Uninstall",
    "Lưu cài đặt trước khi gỡ ứng dụng.": "Save settings before uninstalling the app.",
    "Gỡ cài đặt re/read khỏi máy tính?": "Uninstall re/read from this computer?",
    "Toàn bộ ứng dụng, lịch sử, cài đặt và mô hình đã tải sẽ bị xóa.": "The app, history, settings, and downloaded models will all be removed.",
    "Không tìm thấy trình gỡ cài đặt trong thư mục ứng dụng.": "The uninstaller was not found in the application folder.",
    "Không thể mở trình gỡ cài đặt: ": "Could not start the uninstaller: ",
    "Hủy": "Cancel",
    "Dịch văn bản": "Translate text",
    "DỊCH SANG": "TRANSLATE TO",
    "Ngôn ngữ đích": "Target language",
    "Văn bản nguồn": "Source text",
    "Tự nhận diện": "Auto-detect",
    "Nhập hoặc dán văn bản cần dịch…": "Type or paste text to translate…",
    "Văn bản cần dịch": "Text to translate",
    "Văn bản chỉ được xử lý trên máy.": "Text is processed on this device.",
    "Xóa": "Clear",
    "Bản dịch": "Translation",
    "Sao chép": "Copy",
    "Bản dịch sẽ xuất hiện ở đây.": "Your translation will appear here.",
    "Kết quả dịch": "Translation result",
    "Bắt đầu nhanh": "Quick start",
    "Cài mô hình": "Get models",
    "Chọn nơi lưu": "Choose storage",
    "Chưa có mô hình đã cài": "No installed models",
    "Chưa có mô hình. Cài một lần để bắt đầu dịch ngoại tuyến.": "No models installed. Download one to start translating offline.",
    "Đã sao chép bản dịch.": "Translation copied.",
    "Đã sao chép": "Copied",
    "Đang dịch…": "Translating…",
    "Lõi sẵn sàng · văn bản được xử lý trên máy": "Engine ready · text is processed on this device",
    "Không có bản dịch.": "No translation available.",
    "Dịch xong.": "Translation complete.",
    "Lịch sử dịch": "Translation history",
    "Xóa lịch sử": "Clear history",
    "Chưa có bản dịch nào": "No translations yet",
    "Bản dịch mới sẽ xuất hiện tại đây khi bật lưu lịch sử.": "Translations will appear here when history is enabled.",
    "Văn bản gốc": "Source text",
    "Sao chép bản dịch": "Copy translation",
    "Lịch sử đã được xóa": "History cleared",
    "Đã xóa ": "Deleted ",
    " bản dịch.": " translations.",
    "Hoàn tác": "Undo",
    "Đóng": "Close",
    "Xóa các bản dịch đã lưu trên máy?": "Delete saved translations from this device?",
    "Bạn có thể hoàn tác ngay sau khi xóa.": "You can undo this immediately after deleting.",
    "Mô hình ngôn ngữ": "Language models",
    "Tìm hướng dịch": "Search translation pairs",
    "Tìm mô hình": "Search models",
    "Chọn một mô hình": "Select a model",
    "Tải mô hình": "Download model",
    "Gỡ mô hình": "Remove model",
    "mô hình": "model",
    "Mở thư mục dữ liệu": "Open data folder",
    "Chưa có mô hình phù hợp": "No matching models",
    "Sẵn sàng": "Ready",
    "Chưa cài": "Not installed",
    "Đã cài": "Installed",
    "Đang tải mô hình…": "Downloading model…",
    "Bạn có thể tải lại sau.": "You can download it again later.",
    "Cài đặt": "Settings",
    "Cách dịch": "Translation behavior",
    "Chọn hành vi khi thao tác trên ứng dụng khác.": "Choose how translation works in other apps.",
    "Giữ chuột để dịch": "Hold the mouse button to translate",
    "giây": "seconds",
    "Nhấn Ctrl + C hai lần để dịch": "Press Ctrl + C twice to translate",
    "Nhấn Ctrl + V hai lần để mở lịch sử": "Press Ctrl + V twice to open history",
    "Tự đóng thẻ dịch": "Close translation popup automatically",
    "Kéo chọn": "Text selection",
    "Thời gian giữ": "Hold duration",
    "Phím tắt": "Shortcuts",
    "Lịch sử nhanh": "Quick history",
    "Thẻ dịch": "Translation popup",
    "Đóng sau": "Close after",
    "Quyền riêng tư": "Privacy",
    "Văn bản, lịch sử và nhật ký được lưu cục bộ. Lịch sử không tự xóa và có thể tắt bất cứ lúc nào.": "Text, history, and logs stay on this device. History is not cleared automatically and can be disabled at any time.",
    "Lưu toàn bộ lịch sử bản dịch trên máy": "Save translation history on this device",
    "Khởi động cùng Windows": "Start with Windows",
    "Mở re/read khi đăng nhập Windows (chạy nền)": "Start re/read in the background when you sign in to Windows",
    "Dữ liệu ứng dụng": "App data",
    "Thư mục lưu mô hình": "Model folder",
    "Chọn thư mục…": "Choose folder…",
    "Thư mục mô hình": "Model folder",
    "Model tải về được lưu trong thư mục này. Đổi vị trí có hiệu lực sau khi mở lại app; chọn thư mục cũ để dùng lại model đã tải.": "Downloaded models are stored here. A folder change takes effect after restarting; select the previous folder to reuse downloaded models.",
    "Mọi thay đổi đã được lưu": "All changes saved",
    "Có thay đổi chưa lưu": "Unsaved changes",
    "Lưu thay đổi": "Save changes",
    "Lưu thay đổi sẽ đăng ký chạy nền khi đăng nhập Windows.": "Saving will enable background startup when you sign in to Windows.",
    "Lưu thay đổi sẽ gỡ mục tự khởi động của re/read.": "Saving will remove re/read from Windows startup.",
    "Đã đăng ký khởi động cùng Windows.": "Registered to start with Windows.",
    "Ứng dụng không tự chạy khi đăng nhập Windows.": "The app does not start automatically when you sign in.",
    "Đã hoàn tác thay đổi.": "Changes undone.",
    "Không thể dùng thư mục mô hình": "Model folder unavailable",
    "Không thể tạo hoặc mở thư mục đã chọn: ": "Could not create or open the selected folder: ",
    "Không thể cập nhật khởi động": "Could not update startup settings",
    "Đã tắt khởi động và gỡ mục đăng ký của re/read.": "Startup disabled and re/read removed from startup.",
    "Đã bật khởi động cùng Windows.": "Start with Windows enabled.",
    "Đã lưu cài đặt.": "Settings saved.",
    " Mở lại ứng dụng để dùng thư mục mô hình mới.": " Restart the app to use the new model folder.",
    "Chọn thư mục lưu mô hình": "Choose a folder for models",
    "Nhật ký hoạt động": "Activity log",
    "Xóa nhật ký": "Clear log",
    "Lưu đầy đủ trong SQLite; màn hình hiển thị 2.000 dòng mới nhất.": "Stored in SQLite; this page shows the latest 2,000 entries.",
    "Nhật ký ứng dụng": "App log",
    "Xóa nhật ký cục bộ của ứng dụng?": "Delete the app's local log?",
    "Dịch": "Translate",
    "Lịch sử": "History",
    "Mô hình": "Models",
    "Nhật ký": "Log",
    "Làm việc": "Workspace",
    "Tiện ích": "Tools",
    "Bản dịch được xử lý cục bộ": "Translations are processed locally",
    "Đang khởi động…": "Starting…",
    "Tạm dừng": "Pause",
    "Tiếp tục": "Resume",
    "Đang tạm dừng": "Paused",
    "Đang hoạt động": "Active",
    "Không dịch được văn bản": "Could not translate the selected text",
    "Ngôn ngữ giao diện": "Interface language",
    "Khởi động lại ứng dụng để áp dụng ngôn ngữ mới.": "Restart the app to apply the new language.",
    "Thiết lập re/read": "Set up re/read",
    "Chọn nơi lưu mô hình": "Choose where to store models",
    "Chọn thư mục để lưu các mô hình dịch. Ứng dụng chưa tải mô hình nào; bạn có thể tải từng mô hình sau trong mục Mô hình.": "Choose a folder for translation models. No models have been downloaded; you can download them later from Models.",
    "Duyệt…": "Browse…",
    "Hoàn tất thiết lập": "Finish setup",
    "Không thể lưu thiết lập vào thư mục dữ liệu của ứng dụng.": "Could not save setup to the app data folder.",
    "Không thể thiết lập thư mục này: ": "Could not set up this folder: ",
    "Tiếng Việt (VI)": "Vietnamese (VI)",
    "Tiếng Anh (EN)": "English (EN)",
    "ĐÃ CÀI": "INSTALLED",
    "Có thể tải": "Available to download",
    "Tải xuống khoảng ": "Download about ",
    "Không thể tải ": "Could not download ",
    "Gỡ mô hình ": "Remove model ",
    " khỏi máy?": " from this device?",
    "Lỗi khi dịch văn bản": "Translation error",
    "Đang hoạt động · dịch ngoại tuyến": "Active · offline translation",
    "Đang tạm dừng · dịch ngoại tuyến": "Paused · offline translation",
    "Mở re/read": "Open re/read",
    "Thoát": "Quit",
    "✓ SẴN SÀNG": "✓ READY",
    "✓ ĐÃ CÀI": "✓ INSTALLED",
    "Mở trang ": "Open page ",
    "Đã cài ": "Installed ",
    "MB trên đĩa": "MB on disk",
    "1. Tải mô hình cần dùng ở trang Mô hình. Mô hình được lưu trên máy; sau đó bạn có thể dịch ngoại tuyến.\n"
    "2. Bôi đen văn bản ở ứng dụng khác rồi giữ chuột 2 giây, hoặc nhấn Ctrl+C hai lần.\n"
    "3. Bạn cũng có thể dán văn bản vào ô bên trái. Nhấn Ctrl+V hai lần để mở lịch sử.":
    "1. Download a model from Models. It is stored on this device so you can translate offline.\n"
    "2. Select text in another app, then hold the mouse button for 2 seconds or press Ctrl+C twice.\n"
    "3. You can also paste text into the box on the left. Press Ctrl+V twice to open history.",
    "Không thể khởi động lõi dịch: ": "Could not start the translation engine: ",
    "Bản dịch chưa hoàn tất": "Translation is incomplete",
}

_LANGUAGE_NAMES = {
    "Tiếng Việt": "Vietnamese",
    "Tiếng Anh": "English",
    "Tiếng Trung (Giản thể)": "Chinese (Simplified)",
    "Tiếng Trung": "Chinese",
    "Tiếng Nga": "Russian",
    "Tiếng Nhật": "Japanese",
}


def set_ui_language(language: str) -> str:
    global _LANGUAGE
    _LANGUAGE = language if language in ("vi", "en") else "vi"
    return _LANGUAGE


def ui_language() -> str:
    return _LANGUAGE


def translate(text: str, language: str | None = None) -> str:
    selected = language or _LANGUAGE
    if selected != "en":
        for source, translated in _ENGLISH.items():
            if text == translated:
                return source
        for source, translated in _LANGUAGE_NAMES.items():
            text = text.replace(translated, source)
        return text

    if text in _ENGLISH:
        return _ENGLISH[text]
    for source, translated in sorted(_LANGUAGE_NAMES.items(), key=lambda item: -len(item[0])):
        text = text.replace(source, translated)
    return text


def localize_widgets(root: QWidget, language: str | None = None) -> None:
    """Translate the current static text of a page or dialog tree."""
    for widget in (root, *root.findChildren(QWidget)):
        if widget.objectName() in {"historyContentText", "dataPath"}:
            continue
        if isinstance(widget, (QLabel, QPushButton, QCheckBox)):
            widget.setText(translate(widget.text(), language))
        if isinstance(widget, (QLineEdit, QPlainTextEdit, QTextEdit)):
            widget.setPlaceholderText(translate(widget.placeholderText(), language))
        if widget.accessibleName():
            widget.setAccessibleName(translate(widget.accessibleName(), language))
        if isinstance(widget, QComboBox):
            for index in range(widget.count()):
                widget.setItemText(index, translate(widget.itemText(index), language))

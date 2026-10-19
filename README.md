# re/read Desktop

Ứng dụng desktop dịch văn bản ngoại tuyến. Chọn một đoạn văn bản trong ứng dụng khác để dịch gần con trỏ, hoặc nhập trực tiếp trong trang **Dịch**. Sau khi tải mô hình cần dùng, nội dung được dịch ngay trên máy.

[English overview](#english)

## Cài đặt

1. Tải `reread_pyext_setup.exe` từ [GitHub Releases](https://github.com/nvtruongops/reread-pyext/releases).
2. Chọn tiếng Việt hoặc tiếng Anh trong bộ cài. Ứng dụng được cài theo tài khoản Windows hiện tại và có mục gỡ trong **Installed apps / Apps & features**.
3. Ở lần mở đầu tiên, chọn ngôn ngữ giao diện và thư mục lưu mô hình. Có thể đổi ngôn ngữ sau trong **Cài đặt**; cần mở lại ứng dụng để áp dụng.
4. Mở trang **Mô hình**, chọn hướng dịch và bấm **Tải mô hình**. Cần kết nối mạng trong lúc tải; sau đó ứng dụng dịch ngoại tuyến.

Ứng dụng hỗ trợ thao tác bôi đen và nhấn `Ctrl+C` hai lần, dịch văn bản nhập trực tiếp, lịch sử cục bộ, phím tắt và khay hệ thống. Hướng dẫn thao tác cũng có ngay trong trang **Dịch**.

## Dữ liệu và quyền riêng tư

- Cấu hình, lịch sử và nhật ký dùng chung cơ sở dữ liệu tại `%LOCALAPPDATA%\re-read\reread.sqlite3`.
- Mô hình mặc định nằm tại `%LOCALAPPDATA%\re-read\models\reread_pyext`. Có thể chọn một thư mục khác trong thiết lập lần đầu hoặc trang **Cài đặt**.
- Không có mô hình nào trong installer. Chỉ các mô hình bạn chọn mới được tải xuống; bản dịch chạy cục bộ sau khi tải xong.
- Gỡ cài đặt sẽ xóa chương trình, thiết lập, lịch sử, nhật ký và mô hình. Nếu mô hình được lưu ở thư mục tùy chọn bên ngoài, ứng dụng chỉ xóa các tên file có trong registry model và giữ file khác cùng thư mục cha.

## Chạy từ mã nguồn

Yêu cầu Python 3.10 trở lên và Node.js 18 trở lên. Có thể khởi chạy ứng dụng trước khi tải mô hình:

```powershell
python -m pip install -e "app[desktop-build]"
python -m reread_pyext.app
```

Để chạy ở khay hệ thống ngay khi mở:

```powershell
python -m reread_pyext.app --background
```

## Tạo bộ cài Windows

Cài Python 3.12, Node.js 24.19.0 và Inno Setup 6, sau đó cài dependency build và chạy từ PowerShell:

```powershell
python -m pip install -e "app[desktop-build]"
powershell -ExecutionPolicy Bypass -File app\scripts\build_installer.ps1
```

Bộ cài được tạo tại `app\dist\reread_pyext_setup.exe`; bundle chương trình nằm tại `app\dist\reread_pyext.dist`. Script dừng build nếu phát hiện trọng số model trong bundle hoặc Node.js không khớp phiên bản giấy phép đã ghim. Có Visual Studio C++ Build Tools sẽ giúp Qt quét dependency DLL đầy đủ.

## Kiểm tra

Chạy trong thư mục `app`:

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/test_ui_popup.py
python -X utf8 -m compileall -q reread_pyext
```

## Giấy phép

Mã nguồn của dự án phát hành theo MIT; xem [LICENSE](LICENSE). Thành phần vendored và runtime giữ giấy phép riêng; xem [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Trọng số model được tải từ máy chủ upstream khi người dùng chọn model và không nằm trong repo hoặc bộ cài.

---

<a id="english"></a>

## English

re/read Desktop is an offline Windows text translator. The installer and app interface support Vietnamese and English. Choose a language during installation or first-run setup; change it later in **Settings** and restart the app to apply. Choose a model folder on first launch, then download only the models you need from **Models**. No model weights ship with the installer. Translation runs locally after a model is downloaded. Uninstall removes the app's settings, history, logs, and downloaded models; unrelated files in a custom model folder are preserved.

The source is licensed under MIT. Bundled third-party components keep their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

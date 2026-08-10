from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from deep_translator import GoogleTranslator
import srt

app = Flask(__name__)
CORS(app)

@app.route('/translate-srt', methods=['POST'])
def translate_srt():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        target_lang = request.form.get('to', 'fa')
        source_lang = request.form.get('from', 'auto')

        try:
            file_content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            file.seek(0)
            file_content = file.read().decode('windows-1256', errors='ignore')
        
        subtitles = list(srt.parse(file_content))
        translator = GoogleTranslator(source=source_lang, target=target_lang)

        # آرایه‌ای برای ذخیره دیالوگ‌هایی که متن دارند
        valid_subs = [sub for sub in subtitles if sub.content.strip()]
        
        # دسته‌بندی دیالوگ‌ها (هر ۳۰ خط در یک درخواست)
        batch_size = 30
        
        for i in range(0, len(valid_subs), batch_size):
            batch = valid_subs[i:i+batch_size]
            
            # چسباندن متن‌ها با یک جداکننده خاص که گوگل آن را ترجمه نکند (مثل سه خط تیره)
            # این کار باعث می‌شود گوگل همه را در ۱ درخواست ترجمه کند
            separator = "\n---\n"
            combined_text = separator.join([sub.content for sub in batch])
            
            try:
                translated_combined = translator.translate(combined_text)
                # تکه تکه کردن متن ترجمه شده بر اساس همان جداکننده
                translated_lines = translated_combined.split("---")
                
                # قرار دادن متن‌های ترجمه شده در زیرنویس اصلی
                for index, sub in enumerate(batch):
                    if index < len(translated_lines):
                        sub.content = translated_lines[index].strip()
            except Exception:
                # اگر در حالت دسته‌ای خطا داد، این دسته را خط به خط ترجمه کن تا کار خراب نشود
                for sub in batch:
                    try:
                        sub.content = translator.translate(sub.content)
                    except:
                        pass

        final_srt = srt.compose(subtitles)

        return Response(
            final_srt,
            mimetype="text/srt",
            headers={"Content-disposition": f"attachment; filename={file.filename}"}
        )

    except Exception as e:
        return jsonify({'error': 'Translation failed', 'details': str(e)}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({"message": "Batch API is active."})

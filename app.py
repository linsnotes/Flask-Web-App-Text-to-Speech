from flask import Flask, request, render_template, send_file, redirect, url_for
import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import glob
from werkzeug.utils import secure_filename
import codecs

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Ensure the output directory exists
os.makedirs('outputs', exist_ok=True)

# Set the path for the uploads
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed extension you can set your own
ALLOWED_EXTENSIONS = {'xml', 'ssml'}

languages_voices = {
"English (Singapore)": ["en-SG-LunaNeural", "en-SG-WayneNeural"],
"English (United Kingdom)": ["en-GB-SoniaNeural", "en-GB-RyanNeural", "en-GB-LibbyNeural", "en-GB-AbbiNeural", "en-GB-AlfieNeural", "en-GB-BellaNeural", "en-GB-ElliotNeural", "en-GB-EthanNeural", "en-GB-HollieNeural", "en-GB-MaisieNeural", "en-GB-NoahNeural", "en-GB-OliverNeural", "en-GB-OliviaNeural", "en-GB-ThomasNeural"],
"English (United States)": ["en-US-JennyMultilingualNeural", "en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural", "en-US-DavisNeural", "en-US-AmberNeural", "en-US-AnaNeural", "en-US-AshleyNeural", "en-US-BrandonNeural", "en-US-ChristopherNeural", "en-US-CoraNeural", "en-US-ElizabethNeural", "en-US-EricNeural", "en-US-JacobNeural", "en-US-JaneNeural", "en-US-JasonNeural", "en-US-MichelleNeural", "en-US-MonicaNeural", "en-US-NancyNeural", "en-US-RogerNeural", "en-US-SaraNeural", "en-US-SteffanNeural", "en-US-TonyNeural", "en-US-AIGenerate1Neural", "en-US-AIGenerate2Neural", "en-US-AndrewNeural1", "en-US-BlueNeural1", "en-US-BrianNeural", "en-US-EmmaNeural", "en-US-JennyMultilingualV2Neural", "en-US-RyanMultilingualNeural"],
"Chinese (Mandarin, Simplified)": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunyangNeural", "zh-CN-XiaochenNeural", "zh-CN-XiaohanNeural", "zh-CN-XiaomengNeural", "zh-CN-XiaomoNeural", "zh-CN-XiaoqiuNeural", "zh-CN-XiaoruiNeural", "zh-CN-XiaoshuangNeural", "zh-CN-XiaoxuanNeural", "zh-CN-XiaoyanNeural", "zh-CN-XiaoyouNeural", "zh-CN-XiaozhenNeural", "zh-CN-YunfengNeural", "zh-CN-YunhaoNeural", "zh-CN-YunxiaNeural", "zh-CN-YunyeNeural", "zh-CN-YunzeNeural", "zh-CN-XiaorouNeural", "zh-CN-YunjieNeural"],
"Chinese (Mandarin, Taiwanese)": ["zh-TW-HsiaoChenNeural", "zh-TW-YunJheNeural", "zh-TW-HsiaoYuNeural"],
"Chinese (Cantonese, Guangdong)": ["yue-CN-XiaoMinNeural", "yue-CN-YunSongNeural"],
"Chinese (Cantonese, Hong Kong)": ["zh-HK-HiuMaanNeural", "zh-HK-WanLungNeural", "zh-HK-HiuGaaiNeural"],
"Chinese (Shandong Dialect)": ["zh-CN-shandong-YunxiangNeural"],
"Chinese (Liaoning Dialect)": ["zh-CN-liaoning-XiaobeiNeural"],
"Chinese (Sichuan Dialect)": ["zh-CN-sichuan-YunxiNeural"],
"Chinese (Wu Dialect)": ["wuu-CN-XiaotongNeural","wuu-CN-YunzheNeural"],
}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                # Process the SSML file
                output_path = text_to_speech_from_ssml_file(file_path)
                # Redirect to player instead of sending file
                return redirect(url_for('player', filename='output_from_ssml.wav'))
        else:
            # Process the default text
            text = request.form['text']
            if not text.strip():  # Check if the text is not just whitespace
                # Handle the empty text box case appropriately
                # For instance, you can render the form again with an error message
                error_message = "The text box is empty. Please enter some text to synthesize."
                return render_template('index.html', error_message=error_message, languages_voices=languages_voices)

            language_voice = request.form['language_voice']
            language, voice = language_voice.split(':', 1)
            output_path = text_to_speech(text, language, voice)
            # Redirect to player instead of sending file
            return redirect(url_for('player', filename='output.wav'))

    # GET request so render the form
    return render_template('index.html', languages_voices=languages_voices)





def text_to_speech(text, language, voice):
    subscription_key = os.getenv('KEY')
    region = os.getenv('REGION')
    if not subscription_key or not region:
        raise ValueError("Azure credentials not found in .env file")

    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
    speech_config.speech_synthesis_language = language.split(" ")[0].lower() + '-' + language.split(" ")[1]
    speech_config.speech_synthesis_voice_name = voice
    
    audio_output_path = os.path.join('outputs', 'output.wav')
    audio_config = speechsdk.audio.AudioOutputConfig(filename=audio_output_path)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    result = speech_synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesized to [{audio_output_path}] for text [{text}]")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details}")
    else:
        print(f"Speech synthesis failed: {result.reason}")

    return audio_output_path

def text_to_speech_from_ssml_file(ssml_file_path):
    subscription_key = os.getenv('KEY')
    region = os.getenv('REGION')
    if not subscription_key or not region:
        raise ValueError("Azure credentials not found in .env file")

    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
    
    audio_output_path = os.path.join('outputs', 'output_from_ssml.wav')
    audio_config = speechsdk.audio.AudioOutputConfig(filename=audio_output_path)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    with codecs.open(ssml_file_path, 'r', encoding='utf-8', errors='ignore') as ssml_file:
        ssml_content = ssml_file.read()

    result = speech_synthesizer.speak_ssml_async(ssml_content).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesized to [{audio_output_path}] for the SSML document.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
    else:
        print(f"Speech synthesis failed: {result.reason}")

    return audio_output_path

@app.route('/cleanup', methods=['POST'])
def cleanup():
    # Clean up generated .wav files
    output_files = glob.glob('outputs/*.wav')
    for f in output_files:
        try:
            os.remove(f)
            print(f"Deleted output file: {f}")
        except OSError as e:
            print(f"Error deleting output file {f}: {e.strerror}")

    # Clean up uploaded SSML files
    upload_files = glob.glob('uploads/*')
    for f in upload_files:
        try:
            os.remove(f)
            print(f"Deleted uploaded file: {f}")
        except OSError as e:
            print(f"Error deleting uploaded file {f}: {e.strerror}")

    return render_template('cleanup.html'), 200

@app.route('/download', methods=['GET'])
def download():
    output_filename = 'output.wav'  # You can make this dynamic if needed
    output_path = os.path.join('outputs', output_filename)

    if os.path.isfile(output_path):
        return send_file(output_path, as_attachment=True)
    else:
        return render_template('404.html'), 404

@app.route('/audio/<filename>')
def audio(filename):
    return send_file(os.path.join('outputs', filename), mimetype='audio/wav')


@app.route('/player')
def player():
    # Retrieve the filename from the query parameter
    filename = request.args.get('filename', 'output.wav')
    return render_template('player.html', audio_file=filename)

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/language')
def language():
    return render_template('language.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)

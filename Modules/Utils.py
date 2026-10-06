from pathlib import Path
import os
import subprocess

EXCLUDED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
}

class Utils:
    def __init__(self):
        pass

    def split_audio(self, input_file, chunk_seconds=25):
        output_dir = Path("./audios/splitted")
        os.makedirs(output_dir, exist_ok=True)

        output_pattern = os.path.join(output_dir, "chunk_%03d.wav")

        subprocess.run([
            "ffmpeg",
            "-i", str(input_file),
            "-f", "segment",
            "-segment_time", str(chunk_seconds),
            "-ar", "16000",
            "-ac", "1",
            output_pattern
        ], check=True)

        return sorted(output_dir.glob("chunk_*.wav"))
    

    def convert_to_flac(self, file_path: Path):
        output_path = file_path.with_suffix(".flac")

        if file_path.suffix in EXCLUDED_EXTENSIONS:
            return file_path

        # Avoid overwriting an existing FLAC
        if output_path.exists():
            print(f"Skipping: {output_path.name} already exists")
            return output_path

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(file_path),
                    "-vn",              # ignore video streams
                    "-c:a", "flac",
                    str(output_path),
                ],
                check=True
            )

            print(f"Converted: {file_path.name} -> {output_path.name}")
            return output_path

        except subprocess.CalledProcessError:
            print(f"Failed: {file_path.name}")

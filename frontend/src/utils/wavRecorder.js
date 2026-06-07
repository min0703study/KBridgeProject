function mergeBuffers(buffers, totalLength) {
  const result = new Float32Array(totalLength);
  let offset = 0;

  buffers.forEach((buffer) => {
    result.set(buffer, offset);
    offset += buffer.length;
  });

  return result;
}

function writeString(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

function floatTo16BitPcm(view, offset, input) {
  for (let index = 0; index < input.length; index += 1, offset += 2) {
    const sample = Math.max(-1, Math.min(1, input[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);
  floatTo16BitPcm(view, 44, samples);

  return new Blob([view], { type: 'audio/wav' });
}

export async function createWavRecorder() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const audioContext = new AudioContextClass();
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  const buffers = [];
  let totalLength = 0;
  let stopped = false;

  processor.onaudioprocess = (event) => {
    if (stopped) {
      return;
    }

    const channel = event.inputBuffer.getChannelData(0);
    buffers.push(new Float32Array(channel));
    totalLength += channel.length;
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  async function cleanup() {
    stopped = true;
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    if (audioContext.state !== 'closed') {
      await audioContext.close();
    }
  }

  return {
    async stop() {
      await cleanup();
      return encodeWav(mergeBuffers(buffers, totalLength), audioContext.sampleRate);
    },
    async cancel() {
      await cleanup();
    },
  };
}

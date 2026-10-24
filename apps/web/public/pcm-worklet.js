// Turns microphone audio into 16 kHz, 16-bit mono PCM in 100 ms blocks for live speech to text.
class PcmWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.step = sampleRate / 16000; // input samples per output sample
    this.t = 0;
    this.sum = 0;
    this.count = 0;
    this.out = new Int16Array(1600);
    this.n = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;
    for (let i = 0; i < channel.length; i++) {
      this.sum += channel[i];
      this.count += 1;
      this.t += 1;
      if (this.t >= this.step) {
        this.t -= this.step;
        const v = Math.max(-1, Math.min(1, this.sum / this.count));
        this.out[this.n++] = v < 0 ? v * 0x8000 : v * 0x7fff;
        this.sum = 0;
        this.count = 0;
        if (this.n === this.out.length) {
          this.port.postMessage(this.out.slice().buffer);
          this.n = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor('pcm-worklet', PcmWorklet);

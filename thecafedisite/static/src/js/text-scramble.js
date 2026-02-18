class TextScramble {
    constructor(options = {}) {
        // Monocraft's Standard Galactic Alphabet: U+EB40 to U+EB59
        this.glyphSet = options.glyphSet || Array.from({ length: 26 }, (_, i) =>
            String.fromCodePoint(0xEB40 + i)
        ).join('');
        this.duration = options.duration || 2000;
    }

    animate(elements, fromText, toText) {
        return new Promise((resolve) => {
            const maxLength = Math.max(fromText.length, toText.length);
            const queue = this.buildQueue(fromText, toText, maxLength);

            let startTime = null;

            const update = (currentTime) => {
                if (!startTime) startTime = currentTime;
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / this.duration, 1);

                let display = '';

                for (let i = 0; i < queue.length; i++) {
                    const { fromChar, toChar, startProgress, endProgress } = queue[i];

                    if (progress < startProgress) {
                        display += fromChar;
                    } else if (progress >= endProgress) {
                        display += toChar;
                    } else {
                        display += this.randomGlyph();
                    }
                }

                elements.forEach(el => {
                    el.textContent = display;
                });

                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    elements.forEach(el => {
                        el.textContent = toText;
                    });
                    resolve();
                }
            };

            requestAnimationFrame(update);
        });
    }

    buildQueue(fromText, toText, maxLength) {
        const queue = [];

        for (let i = 0; i < maxLength; i++) {
            const fromChar = fromText[i] || ' ';
            const toChar = toText[i] || ' ';

            const startProgress = (i / maxLength) * 0.6;
            const scrambleDuration = 0.2 + Math.random() * 0.2;
            const endProgress = Math.min(startProgress + scrambleDuration, 1);

            queue.push({ fromChar, toChar, startProgress, endProgress });
        }

        return queue;
    }

    randomGlyph() {
        return this.glyphSet[Math.floor(Math.random() * this.glyphSet.length)];
    }
}

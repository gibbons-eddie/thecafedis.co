const BackgroundScrollerAnimator = {
    initialized: false,
    scrambler: null,
    rows: [],
    namePool: [],
    displayDurations: [200, 300, 400, 500],

    init() {
        if (this.initialized) return;

        const container = document.querySelector('.bg-scroller-container');
        if (!container) return;

        this.rows = Array.from(document.querySelectorAll('.bg-scroller-row'));
        if (this.rows.length === 0) return;

        const poolData = container.dataset.namePool;
        if (poolData) {
            try {
                this.namePool = JSON.parse(poolData);
            } catch (e) {
                console.error('Failed to parse name pool:', e);
                return;
            }
        }

        if (this.namePool.length === 0) return;

        this.scrambler = new TextScramble({ duration: 1200 });

        this.initialized = true;

        this.rows.forEach((_, i) => {
            const stagger = Math.random() * 2000;
            setTimeout(() => this.loopRow(i), stagger);
        });
    },

    loopRow(rowIndex) {
        const row = this.rows[rowIndex];
        const spans = row.querySelectorAll('.bg-scroller-text');
        if (spans.length === 0) {
            setTimeout(() => this.loopRow(rowIndex), this.displayDurations[Math.floor(Math.random() * this.displayDurations.length)]);
            return;
        }

        const currentName = spans[0].textContent;
        let newName;
        do {
            newName = this.namePool[Math.floor(Math.random() * this.namePool.length)];
        } while (newName === currentName && this.namePool.length > 1);

        spans.forEach(span => span.classList.add('scrambling'));

        if (typeof ScrollController !== 'undefined') {
            requestAnimationFrame(() => {
                ScrollController.recalculateRow(rowIndex);
            });
        }

        this.scrambler.animate(spans, currentName, newName).then(() => {
            spans.forEach(span => span.classList.remove('scrambling'));
            spans.forEach(span => span.textContent = newName);

            if (typeof ScrollController !== 'undefined') {
                requestAnimationFrame(() => {
                    ScrollController.recalculateRow(rowIndex);
                });
            }

            setTimeout(() => this.loopRow(rowIndex), this.displayDurations[Math.floor(Math.random() * this.displayDurations.length)]);
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    BackgroundScrollerAnimator.init();
});
document.addEventListener('up:fragment:inserted', (event) => {
    if (event.target.querySelector && event.target.querySelector('.bg-scroller-container')) {
        BackgroundScrollerAnimator.initialized = false;
        BackgroundScrollerAnimator.init();
    }
});

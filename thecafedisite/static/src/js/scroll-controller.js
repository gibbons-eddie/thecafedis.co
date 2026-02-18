// JS-controlled transforms using fixed pixel values prevent position jumps
// when font changes occur during text scramble animations.
const ScrollController = {
    rows: [],
    running: false,
    lastTime: 0,
    scrollContainer: null,

    duration: 35000,

    init() {
        const rowElements = document.querySelectorAll('.bg-scroller-row');
        if (rowElements.length === 0) return;

        this.initVerticalScroll();

        this.rows = Array.from(rowElements).map((row, index) => {
            const container = row.querySelector('[class*="animate-scroll-"]');
            if (!container) return null;

            const isLeftScroll = container.classList.contains('animate-scroll-left');
            const scrollDistance = container.offsetWidth * 0.04166;
            container.style.animation = 'none';
            const startOffset = Math.random() * scrollDistance;

            return {
                container,
                isLeftScroll,
                scrollDistance,
                currentPosition: startOffset,
                speed: scrollDistance / this.duration
            };
        }).filter(Boolean);

        if (this.rows.length > 0) {
            this.start();
        }
    },

    start() {
        if (this.running) return;
        this.running = true;
        this.lastTime = performance.now();
        this.tick();
    },

    stop() {
        this.running = false;
    },

    tick() {
        if (!this.running) return;

        const now = performance.now();
        const delta = now - this.lastTime;
        this.lastTime = now;

        for (const row of this.rows) {
            const movement = row.speed * delta;

            if (row.isLeftScroll) {
                row.currentPosition -= movement;
                if (row.currentPosition <= -row.scrollDistance) {
                    row.currentPosition += row.scrollDistance;
                }
            } else {
                row.currentPosition += movement;
                if (row.currentPosition >= 0) {
                    row.currentPosition -= row.scrollDistance;
                }
            }

            row.container.style.transform = `translateX(${row.currentPosition}px)`;
        }

        requestAnimationFrame(() => this.tick());
    },

    initVerticalScroll() {
        this.scrollContainer = document.querySelector('.bg-scroller-container');
        if (!this.scrollContainer) return;

        const updateScroll = () => {
            this.scrollContainer.style.transform = `translateY(${-window.scrollY}px)`;
        };

        window.addEventListener('scroll', updateScroll, { passive: true });
        updateScroll();
    },

    recalculateRow(rowIndex) {
        const row = this.rows[rowIndex];
        if (!row) return;

        const newScrollDistance = row.container.offsetWidth * 0.04166;

        const relativePosition = row.currentPosition / row.scrollDistance;
        row.scrollDistance = newScrollDistance;
        row.currentPosition = relativePosition * newScrollDistance;
        row.speed = newScrollDistance / this.duration;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    ScrollController.init();
});

document.addEventListener('up:fragment:inserted', (event) => {
    if (event.target.querySelector && event.target.querySelector('.bg-scroller-container')) {
        ScrollController.rows = [];
        ScrollController.running = false;
        ScrollController.init();
    }
});

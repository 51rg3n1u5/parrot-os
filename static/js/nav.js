/**
 * ParrotOS Navigation
 * Hanterar navigation mellan appar och startmeny
 */

ParrotOS.nav = {
    currentIndex: 0,
    apps: [],
    
    /**
     * Initiera navigation
     */
    init() {
        this.apps = ParrotOS.apps.filter(app => app.enabled !== false);
        
        // Hitta "home" index
        const homeIndex = this.apps.findIndex(app => app.id === 'home');
        if (homeIndex >= 0) {
            this.currentIndex = homeIndex;
        }
        
        this.updateTitle();
    },
    
    /**
     * Gå till specifik app
     */
    async goTo(appId) {
        // Stoppa current timeout
        ParrotOS.router.clearTimeout();
        
        // Hitta app index
        const index = this.apps.findIndex(app => app.id === appId);
        if (index >= 0) {
            this.currentIndex = index;
        }
        
        // Uppdatera title
        this.updateTitle();
        
        // Ladda app
        await ParrotOS.router.loadApp(appId);
    },
    
    /**
     * Gå till nästa app
     */
    async next() {
        if (this.apps.length === 0) return;
        
        this.currentIndex = (this.currentIndex + 1) % this.apps.length;
        const app = this.apps[this.currentIndex];
        
        await this.goTo(app.id);
    },
    
    /**
     * Gå till föregående app
     */
    async prev() {
        if (this.apps.length === 0) return;
        
        this.currentIndex = (this.currentIndex - 1 + this.apps.length) % this.apps.length;
        const app = this.apps[this.currentIndex];
        
        await this.goTo(app.id);
    },
    
    /**
     * Gå till startmeny (home)
     */
    async home() {
        await this.goTo('home');
    },
    
    /**
     * Uppdatera title i nav bar
     */
    updateTitle() {
        const titleEl = document.getElementById('app-title');
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        
        if (this.apps.length === 0) {
            titleEl.textContent = '🏠 ParrotOS';
            prevBtn.style.display = 'none';
            nextBtn.style.display = 'none';
            return;
        }
        
        const app = this.apps[this.currentIndex];
        const icon = app.icon || '📱';
        titleEl.textContent = `${icon} ${app.name}`;
        
        // Visa/dölj nav buttons baserat på antal appar
        const showNav = this.apps.length > 1;
        prevBtn.style.display = showNav ? 'block' : 'none';
        nextBtn.style.display = showNav ? 'block' : 'none';
    },
    
    /**
     * Callback för navigation events
     */
    onNavigate(callback) {
        // Kan användas för analytics etc
    }
};

// Alias
ParrotOS.goTo = (appId) => ParrotOS.nav.goTo(appId);
ParrotOS.next = () => ParrotOS.nav.next();
ParrotOS.prev = () => ParrotOS.nav.prev();
ParrotOS.home = () => ParrotOS.nav.home();
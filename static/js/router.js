/**
 * ParrotOS Router
 * Laddar appar dynamiskt och hanterar timeouts
 */

ParrotOS.router = {
    apps: [],
    currentApp: null,
    timeoutId: null,
    
    /**
     * Hämta lista på alla tillgängliga appar
     */
    async getApps() {
        try {
            const res = await fetch('/api/apps');
            return await res.json();
        } catch (e) {
            console.error('Failed to load apps:', e);
            return [];
        }
    },
    
    /**
     * Ladda en specifik app
     */
    async loadApp(appId) {
        const container = document.getElementById('app-container');
        container.innerHTML = '<div class="loading">Laddar ' + appId + '...</div>';
        
        try {
            // Hämta app HTML
            const res = await fetch('/api/app/' + appId);
            if (!res.ok) throw new Error('App not found');
            
            const appData = await res.json();
            
            // Skapa app container
            container.innerHTML = `
                <div id="app-${appId}" class="app-wrapper">
                    ${appData.html || ''}
                </div>
            `;
            
            // Kör app-initialisering om den finns
            if (appData.js) {
                eval(appData.js);
            }
            
            // Spara current app
            this.currentApp = appId;
            
            // Starta timeout
            this.startTimeout(appData.timeout_seconds || 60);
            
            return appData;
            
        } catch (e) {
            console.error('Failed to load app:', e);
            container.innerHTML = `
                <div class="app-content">
                    <h2>Fel</h2>
                    <p>Kunde inte ladda app: ${appId}</p>
                    <button class="btn btn-primary" onclick="ParrotOS.nav.home()">
                        Tillbaka hem
                    </button>
                </div>
            `;
            return null;
        }
    },
    
    /**
     * Starta timeout för app
     */
    startTimeout(seconds) {
        this.clearTimeout();
        
        if (!seconds || seconds <= 0) return;
        
        this.timeoutId = setTimeout(() => {
            console.log('Timeout reached, going home');
            ParrotOS.nav.home();
        }, seconds * 1000);
        
        console.log('Timeout started:', seconds + 's');
    },
    
    /**
     * Nollställ timeout (anropas vid touch)
     */
    resetTimeout() {
        if (this.currentApp && this.timeoutId) {
            // Hämta timeout från current app
            const app = ParrotOS.apps.find(a => a.id === this.currentApp);
            if (app && app.timeout_seconds) {
                this.startTimeout(app.timeout_seconds);
            }
        }
    },
    
    /**
     * Rensa timeout
     */
    clearTimeout() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
    }
};

// Alias för enkel åtkomst
ParrotOS.loadApp = (appId) => ParrotOS.router.loadApp(appId);
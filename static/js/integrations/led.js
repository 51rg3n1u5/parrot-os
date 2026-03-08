/**
 * ParrotOS - LED Integration (WLED)
 * Kontrollerar LED-strips via WLED API
 */

ParrotOS.led = {
    // Default WLED IP (kan konfigureras)
    ip: '192.168.1.100',
    
    /**
     * Sätt effekt
     */
    async setEffect(effect) {
        try {
            // Map effect names to WLED API calls
            const effects = {
                'rainbow': { seg: [{fx: 0, sx: 128, ix: 128}] },
                'solid': { seg: [{fx: 1, col: [[255,100,0]]}] },
                'pulse': { seg: [{fx: 2, sx: 100, ix: 150}] },
                'off': { on: false },
                'on': { on: true, seg: [{fx: 1, col: [[255,200,100]]}] },
                'calm': { seg: [{fx: 1, col: [[50,80,150]]}] },
                'excited': { seg: [{fx: 0, sx: 200, ix: 200}] },
                'party': { seg: [{fx: 17, sx: 150, ix: 100}] }
            };
            
            const body = effects[effect] || effects.off;
            
            const res = await fetch('http://' + this.ip + '/json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            if (!res.ok) throw new Error('WLED error');
            
            return { success: true, effect: effect };
        } catch (e) {
            console.error('LED error:', e);
            return { success: false, error: e.message };
        }
    },
    
    /**
     * Sätt specifik färg
     */
    async setColor(r, g, b) {
        try {
            const res = await fetch('http://' + this.ip + '/json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    on: true,
                    seg: [{ fx: 1, col: [[r, g, b]] }]
                })
            });
            
            return { success: true, color: [r, g, b] };
        } catch (e) {
            return { success: false, error: e.message };
        }
    },
    
    /**
     * Stäng av
     */
    async off() {
        return await this.setEffect('off');
    },
    
    /**
     * Stäng på
     */
    async on() {
        return await this.setEffect('on');
    },
    
    /**
     * Kolla status
     */
    async status() {
        try {
            const res = await fetch('http://' + this.ip + '/json');
            const data = await res.json();
            
            return {
                on: data.on,
                brightness: data.dly || 0,
                effect: data.seg?.[0]?.fx || 0
            };
        } catch (e) {
            return { error: e.message, connected: false };
        }
    },
    
    /**
     * Sätt IP (konfiguration)
     */
    setIP(ip) {
        this.ip = ip;
    }
};

// Convenience functions for HTML
async function ledEffect(effect) {
    return await ParrotOS.led.setEffect(effect);
}

async function ledOff() {
    return await ParrotOS.led.off();
}
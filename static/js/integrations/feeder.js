/**
 * ParrotOS - Feeder Integration
 * Kontrollerar pellet-feeder via API
 */

ParrotOS.feeder = {
    /**
     * Ge pellets
     */
    async dispense(grams = 10) {
        try {
            const res = await fetch('/api/feed?amount=' + grams, { 
                method: 'POST' 
            });
            const data = await res.json();
            
            if (data.error) {
                console.error('Feed error:', data.error);
                return { success: false, error: data.error };
            }
            
            return { 
                success: true, 
                dispensed: grams, 
                total: data.total_today 
            };
        } catch (e) {
            console.error('Feeder error:', e);
            return { success: false, error: e.message };
        }
    },
    
    /**
     * Hämta status
     */
    async getStatus() {
        try {
            const res = await fetch('/api/state');
            const state = await res.json();
            
            return {
                pelletsToday: state.pellets_today,
                pelletBudget: state.pellet_budget,
                bonusEarned: state.bonus_earned,
                lastFeeding: state.last_feeding
            };
        } catch (e) {
            return { error: e.message };
        }
    },
    
    /**
     * Kvarvarande budget
     */
    async getBudget() {
        const status = await this.getStatus();
        if (status.error) return 0;
        
        return Math.max(0, status.pelletBudget - status.pelletsToday + status.bonusEarned);
    }
};

// Convenience function for HTML
async function feedPets(grams = 10) {
    return await ParrotOS.feeder.dispense(grams);
}
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
    try {
        const response = await fetch('/api/status/prompts');
        if (response.ok) {
            const prompts = await response.json();
            return { prompts };
        }
    } catch (e) {
        console.error('Failed to load prompts:', e);
    }
    return { prompts: null };
};

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
    try {
        const res = await fetch('/api/matching/history?limit=100');
        const matches = await res.json();
        return { matches };
    } catch (e) {
        return { matches: [], error: "Kon match-historie niet ophalen." };
    }
};

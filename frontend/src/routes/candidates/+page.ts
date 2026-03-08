import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
    try {
        const res = await fetch('/api/candidates/');
        const candidates = await res.json();
        return { candidates };
    } catch (e) {
        return { candidates: [], error: "Kon kandidaten niet ophalen." };
    }
};

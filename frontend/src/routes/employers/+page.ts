import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
    try {
        const res = await fetch('/api/employers/');
        const employers = await res.json();
        return { employers };
    } catch (e) {
        return { employers: [], error: "Kon werkgeversvragen niet ophalen." };
    }
};

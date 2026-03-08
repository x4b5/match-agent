import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
    try {
        const [candRes, empRes] = await Promise.all([
            fetch('/api/candidates/'),
            fetch('/api/employers/')
        ]);
        
        const candidates = await candRes.json();
        const employers = await empRes.json();
        
        // Filter those who have a profile
        const readyCandidates = candidates.filter((c: any) => c.has_profile);
        const readyEmployers = employers.filter((e: any) => e.has_profile);

        return { candidates: readyCandidates, employers: readyEmployers };
    } catch (e) {
        return { candidates: [], employers: [], error: "Kon data niet laden." };
    }
};

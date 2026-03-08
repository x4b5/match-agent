import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
    try {
        const [statusRes, candidatesRes, employersRes] = await Promise.all([
            fetch('/api/status/'),
            fetch('/api/candidates/'),
            fetch('/api/employers/')
        ]);

        const statusData = await statusRes.json();
        const candidatesData = await candidatesRes.json();
        const employersData = await employersRes.json();

        return {
            ollama: statusData,
            candidates: candidatesData,
            employers: employersData
        };
    } catch (e) {
        return {
            ollama: { online: false, models: [] },
            candidates: [],
            employers: [],
            error: "Kon geen backend bereiken."
        };
    }
};

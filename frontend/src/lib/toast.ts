import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
    id: number;
    message: string;
    type: ToastType;
}

let nextId = 0;

function createToastStore() {
    const { subscribe, update } = writable<Toast[]>([]);

    function add(message: string, type: ToastType = 'info', duration = 4000) {
        const id = nextId++;
        update(toasts => [...toasts, { id, message, type }]);
        if (duration > 0) {
            setTimeout(() => remove(id), duration);
        }
    }

    function remove(id: number) {
        update(toasts => toasts.filter(t => t.id !== id));
    }

    return { subscribe, add, remove };
}

export const toasts = createToastStore();

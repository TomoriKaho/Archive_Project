import { defineStore } from 'pinia';

let toastId = 0;

export const useUiStore = defineStore('ui', {
  state: () => ({
    isSidebarCollapsed: false,
    toasts: [],
    activeModal: null,
    modalPayload: null
  }),
  actions: {
    toggleSidebar() {
      this.isSidebarCollapsed = !this.isSidebarCollapsed;
    },
    showToast({ message, type = 'info', timeout = 4000 }) {
      const id = ++toastId;
      this.toasts.push({ id, message, type });
      if (timeout) {
        setTimeout(() => this.removeToast(id), timeout);
      }
    },
    removeToast(id) {
      this.toasts = this.toasts.filter((toast) => toast.id !== id);
    },
    openModal(name, payload = null) {
      this.activeModal = name;
      this.modalPayload = payload;
    },
    closeModal() {
      this.activeModal = null;
      this.modalPayload = null;
    }
  }
});

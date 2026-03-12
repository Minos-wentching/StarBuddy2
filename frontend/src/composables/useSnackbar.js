import { ref } from 'vue'

// 简单的snackbar管理器
export function useSnackbar() {
  const message = ref('')
  const color = ref('')
  const show = ref(false)
  const timeout = ref(3000)

  const showSnackbar = (msg, type = 'info') => {
    message.value = msg
    color.value = getColor(type)
    show.value = true

    // 自动隐藏
    setTimeout(() => {
      show.value = false
    }, timeout.value)
  }

  const getColor = (type) => {
    switch (type) {
      case 'success': return 'green'
      case 'error': return 'red'
      case 'warning': return 'orange'
      case 'info':
      default: return 'blue'
    }
  }

  return {
    message,
    color,
    show,
    showSnackbar
  }
}

// 全局snackbar组件（需要在App.vue中注册）
export function createSnackbarComponent() {
  return {
    setup() {
      const { message, color, show, showSnackbar } = useSnackbar()

      // 暴露给全局
      window.$snackbar = showSnackbar

      return {
        message,
        color,
        show
      }
    },
    template: `
      <v-snackbar v-model="show" :color="color" :timeout="3000" location="top">
        {{ message }}
      </v-snackbar>
    `
  }
}
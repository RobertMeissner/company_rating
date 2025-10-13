import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#2c3e50',
          secondary: '#3498db',
          accent: '#27ae60',
          error: '#e74c3c',
          warning: '#f39c12',
          info: '#17a2b8',
          success: '#27ae60',
        },
      },
    },
  },
  icons: {
    defaultSet: 'mdi',
  },
})

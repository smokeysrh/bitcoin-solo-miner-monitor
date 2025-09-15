<template>
  <v-card flat>
    <v-card-text>
      <v-container>
        <v-row>
          <v-col cols="12" class="text-center">
            <h2 class="text-h5 mb-4">Configure Notifications</h2>
            <p class="text-body-1 mb-6">
              Choose how you want to be notified when this alert is triggered.
            </p>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="primary">mdi-bell-outline</v-icon>
                Notification Methods
              </v-card-title>
              <v-card-text>
                <v-form ref="notificationsForm" v-model="isFormValid">
                  <v-checkbox
                    v-model="notifications.methods"
                    label="In-App Notifications"
                    value="app"
                    hide-details
                    class="mb-2"
                  ></v-checkbox>

                  <v-checkbox
                    v-model="notifications.methods"
                    label="Email Notifications"
                    value="email"
                    hide-details
                    class="mb-2"
                  ></v-checkbox>

                  <v-expand-transition>
                    <div
                      v-if="notifications.methods.includes('email')"
                      class="ml-8 mb-4"
                    >
                      <v-text-field
                        v-model="notifications.email"
                        label="Email Address"
                        outlined
                        dense
                        :rules="[(v) => !!v || 'Email is required', emailRule]"
                      ></v-text-field>
                    </div>
                  </v-expand-transition>

                  <v-checkbox
                    v-model="notifications.methods"
                    label="SMS Notifications"
                    value="sms"
                    hide-details
                    class="mb-2"
                  ></v-checkbox>

                  <v-expand-transition>
                    <div
                      v-if="notifications.methods.includes('sms')"
                      class="ml-8 mb-4"
                    >
                      <v-text-field
                        v-model="notifications.phone"
                        label="Phone Number"
                        outlined
                        dense
                        hint="Include country code (e.g., +1 555-123-4567)"
                        persistent-hint
                        :rules="[
                          (v) => !!v || 'Phone number is required',
                          phoneRule,
                        ]"
                      ></v-text-field>
                    </div>
                  </v-expand-transition>

                  <v-checkbox
                    v-model="notifications.methods"
                    label="Webhook"
                    value="webhook"
                    hide-details
                    class="mb-2"
                  ></v-checkbox>

                  <v-expand-transition>
                    <div
                      v-if="notifications.methods.includes('webhook')"
                      class="ml-8 mb-4"
                    >
                      <v-text-field
                        v-model="notifications.webhook_url"
                        label="Webhook URL"
                        outlined
                        dense
                        hint="URL that will receive alert data"
                        persistent-hint
                        :rules="[
                          (v) => !!v || 'Webhook URL is required',
                          urlRule,
                        ]"
                      ></v-text-field>
                    </div>
                  </v-expand-transition>

                  <v-alert
                    v-if="notifications.methods.length === 0"
                    type="warning"
                    outlined
                    dense
                    class="mt-4"
                  >
                    Please select at least one notification method.
                  </v-alert>
                </v-form>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row class="mt-4">
          <v-col cols="12">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="primary">mdi-clock-outline</v-icon>
                Notification Frequency
              </v-card-title>
              <v-card-text>
                <v-radio-group
                  v-model="notifications.frequency"
                  :mandatory="true"
                >
                  <v-radio
                    label="Once (notify only when alert is first triggered)"
                    value="once"
                  ></v-radio>
                  <v-radio
                    label="Every occurrence (notify each time the condition is met)"
                    value="every_occurrence"
                  ></v-radio>
                  <v-radio
                    label="Hourly summary (group notifications by hour)"
                    value="hourly"
                  ></v-radio>
                  <v-radio
                    label="Daily summary (group notifications by day)"
                    value="daily"
                  ></v-radio>
                </v-radio-group>

                <v-divider class="my-4"></v-divider>

                <v-switch
                  v-model="notifications.quiet_hours.enabled"
                  label="Enable Quiet Hours"
                  hint="Don't send notifications during specified hours"
                  persistent-hint
                  class="mb-4"
                ></v-switch>

                <v-expand-transition>
                  <div v-if="notifications.quiet_hours.enabled">
                    <v-row>
                      <v-col cols="12" sm="6">
                        <v-text-field
                          v-model="notifications.quiet_hours.start"
                          label="Start Time"
                          type="time"
                          outlined
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" sm="6">
                        <v-text-field
                          v-model="notifications.quiet_hours.end"
                          label="End Time"
                          type="time"
                          outlined
                        ></v-text-field>
                      </v-col>
                    </v-row>
                  </div>
                </v-expand-transition>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="showHelp" class="mt-4">
          <v-col cols="12">
            <v-alert type="info" outlined>
              <h3 class="text-subtitle-1 font-weight-bold">
                About Notifications
              </h3>
              <p class="mb-0">
                Choose at least one notification method. You can set the
                frequency of notifications and enable quiet hours to prevent
                notifications during specific times.
              </p>
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, watch } from "vue";

export default {
  name: "AlertNotifications",

  props: {
    alertData: {
      type: Object,
      required: true,
    },

    showHelp: {
      type: Boolean,
      default: true,
    },
  },

  setup(props, { emit }) {
    // State
    const isFormValid = ref(false);
    const notifications = ref({
      methods: props.alertData.notifications?.methods || ["app"],
      email: props.alertData.notifications?.email || "",
      phone: props.alertData.notifications?.phone || "",
      webhook_url: props.alertData.notifications?.webhook_url || "",
      frequency: props.alertData.notifications?.frequency || "once",
      quiet_hours: {
        enabled: props.alertData.notifications?.quiet_hours?.enabled || false,
        start: props.alertData.notifications?.quiet_hours?.start || "22:00",
        end: props.alertData.notifications?.quiet_hours?.end || "08:00",
      },
    });

    // Validation rules
    const emailRule = (value) => {
      if (!value) return true;
      const pattern =
        /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
      return pattern.test(value) || "Invalid email address";
    };

    const phoneRule = (value) => {
      if (!value) return true;
      const pattern = /^\+?[1-9]\d{1,14}$/;
      return pattern.test(value.replace(/\D/g, "")) || "Invalid phone number";
    };

    const urlRule = (value) => {
      if (!value) return true;
      try {
        new URL(value);
        return true;
      } catch (e) {
        return "Invalid URL";
      }
    };

    // Watch for changes
    watch(
      notifications,
      () => {
        emit("update-notifications", notifications.value);
      },
      { deep: true },
    );

    return {
      isFormValid,
      notifications,
      emailRule,
      phoneRule,
      urlRule,
    };
  },
};
</script>

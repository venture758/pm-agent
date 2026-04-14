import { createRouter, createWebHistory } from "vue-router";

import IntakeView from "../views/IntakeView.vue";
import ModuleManagementView from "../views/ModuleManagementView.vue";
import PersonnelManagementView from "../views/PersonnelManagementView.vue";
import RecommendationsView from "../views/RecommendationsView.vue";
import DeliveryView from "../views/DeliveryView.vue";
import MonitoringView from "../views/MonitoringView.vue";
import ConfirmationHistoryView from "../views/ConfirmationHistoryView.vue";
import InsightsView from "../views/InsightsView.vue";

const routes = [
  {
    path: "/",
    redirect: "/workspaces/default/intake",
  },
  {
    path: "/workspaces/:workspaceId/intake",
    name: "intake",
    component: IntakeView,
  },
  {
    path: "/workspaces/:workspaceId/modules",
    name: "modules",
    component: ModuleManagementView,
  },
  {
    path: "/workspaces/:workspaceId/personnel",
    name: "personnel",
    component: PersonnelManagementView,
  },
  {
    path: "/workspaces/:workspaceId/recommendations",
    name: "recommendations",
    component: RecommendationsView,
  },
  {
    path: "/workspaces/:workspaceId/delivery",
    name: "delivery",
    component: DeliveryView,
  },
  {
    path: "/workspaces/:workspaceId/monitoring",
    name: "monitoring",
    component: MonitoringView,
  },
  {
    path: "/workspaces/:workspaceId/confirmations",
    name: "confirmations",
    component: ConfirmationHistoryView,
  },
  {
    path: "/workspaces/:workspaceId/insights",
    name: "insights",
    component: InsightsView,
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});

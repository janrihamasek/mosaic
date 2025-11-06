import apiClient from "../apiClient";

export async function fetchCurrentUser() {
  const response = await apiClient.get("/user");
  return response.data;
}

export async function updateCurrentUser(payload) {
  const response = await apiClient.patch("/user", payload);
  return response.data;
}

export async function deleteCurrentUser() {
  await apiClient.delete("/user");
}

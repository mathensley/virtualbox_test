from locust import HttpUser, task, constant


class UsuarioCPU(HttpUser):
    wait_time = constant(0.5)

    @task
    def calcular_primos(self):
        self.client.get("/cpu?n=100000")
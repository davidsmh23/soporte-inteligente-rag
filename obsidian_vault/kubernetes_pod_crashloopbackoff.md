---
id_ticket: #2422
tecnologia: Kubernetes, K8s, DevOps, Contenedores
autor: David_Admin
---
# Problema: Pod en estado CrashLoopBackOff en el clúster de staging
El pod `api-deployment-7f8d9c-xkp2q` en el namespace `staging` entra en bucle de reinicios. El estado en `kubectl get pods` muestra `CrashLoopBackOff` con más de 20 reinicios.

# Solución Exitosa:
El pod no arrancaba porque el ConfigMap referenciado en el Deployment apuntaba a una clave inexistente.
1. Lee los logs del pod: `kubectl logs api-deployment-7f8d9c-xkp2q -n staging --previous`
2. El error `env variable APP_SECRET not found` confirma la causa.
3. Inspecciona el ConfigMap: `kubectl describe configmap app-config -n staging`
4. La clave era `APP_SECRET_KEY` pero el Deployment buscaba `APP_SECRET`. Corrige el nombre en el manifiesto del Deployment bajo `env.valueFrom.configMapKeyRef.key`.
5. Aplica los cambios: `kubectl apply -f deployment.yaml` y verifica que los pods se estabilicen.

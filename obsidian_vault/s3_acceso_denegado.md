---
id_ticket: #2409
tecnologia: AWS, S3, IAM, Cloud
autor: Laura_Infra
---
# Problema: La aplicación en producción lanza "AccessDenied" al leer archivos de S3
Tras un despliegue del servicio de almacenamiento, la aplicación lanza `botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the GetObject operation`. Los archivos existen en el bucket confirmado.

# Solución Exitosa:
El despliegue había rotado el rol IAM de la instancia EC2 y el nuevo rol no tenía los permisos `s3:GetObject` y `s3:ListBucket` sobre el bucket de producción.
1. En la consola de AWS IAM, localiza el rol asociado a la instancia EC2 (EC2 > Instances > selecciona la instancia > IAM Role).
2. Revisa las políticas adjuntas y busca si existe una que cubra el bucket afectado.
3. Si no existe, crea una política en línea con: `s3:GetObject` y `s3:ListBucket` sobre el ARN `arn:aws:s3:::nombre-del-bucket` y `arn:aws:s3:::nombre-del-bucket/*`.
4. Adjunta la política al rol y espera 30 segundos para que se propague. Vuelve a probar la aplicación.
